from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social_poster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# =========================
# МОДЕЛИ БАЗЫ ДАННЫХ
# =========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    password_hash = db.Column(db.String(200))
    google_id = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    social_accounts = db.relationship('SocialAccount', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)

class SocialAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    platform_user_id = db.Column(db.String(200))
    platform_username = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(50))
    youtube_enabled = db.Column(db.Boolean, default=False)
    youtube_title = db.Column(db.String(100))
    youtube_description = db.Column(db.Text)
    youtube_tags = db.Column(db.String(500))
    youtube_status = db.Column(db.String(50))
    youtube_video_id = db.Column(db.String(100))
    instagram_enabled = db.Column(db.Boolean, default=False)
    instagram_caption = db.Column(db.Text)
    instagram_status = db.Column(db.String(50))
    instagram_post_id = db.Column(db.String(100))
    tiktok_enabled = db.Column(db.Boolean, default=False)
    tiktok_caption = db.Column(db.Text)
    tiktok_status = db.Column(db.String(50))
    tiktok_video_id = db.Column(db.String(100))
    vk_enabled = db.Column(db.Boolean, default=False)
    vk_caption = db.Column(db.Text)
    vk_status = db.Column(db.String(50))
    vk_post_id = db.Column(db.String(100))
    schedule_type = db.Column(db.String(20), default='now')
    scheduled_time = db.Column(db.DateTime)
    timezone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='draft')

# =========================
# ПОЛУЧЕНИЕ ДЕФОЛТНОГО ПОЛЬЗОВАТЕЛЯ (БЕЗ АВТОРИЗАЦИИ)
# =========================

def get_default_user():
    """Создаёт или возвращает дефолтного пользователя"""
    with app.app_context():
        user = User.query.first()
        if not user:
            # Создаём дефолтного пользователя
            user = User(
                email='admin@local',
                name='Admin',
                google_id=None
            )
            db.session.add(user)
            db.session.commit()
        return user

# =========================
# МАРШРУТЫ
# =========================

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    user = get_default_user()
    connected_platforms = {
        'youtube': SocialAccount.query.filter_by(user_id=user.id, platform='youtube', is_active=True).first(),
        'instagram': SocialAccount.query.filter_by(user_id=user.id, platform='instagram', is_active=True).first(),
        'tiktok': SocialAccount.query.filter_by(user_id=user.id, platform='tiktok', is_active=True).first(),
        'vk': SocialAccount.query.filter_by(user_id=user.id, platform='vk', is_active=True).first(),
    }
    return render_template('dashboard.html', connected=connected_platforms, user=user)

@app.route('/settings')
def settings():
    user = get_default_user()
    social_accounts = SocialAccount.query.filter_by(user_id=user.id).all()
    platforms_status = {'youtube': False, 'instagram': False, 'tiktok': False, 'vk': False}
    for account in social_accounts:
        if account.is_active:
            platforms_status[account.platform] = account
    return render_template('settings.html', platforms=platforms_status, user=user)

@app.route('/api/publish', methods=['POST'])
def publish_post():
    try:
        user = get_default_user()
        data = request.form
        file = request.files.get('video')
        
        post = Post(
            user_id=user.id,
            youtube_enabled=data.get('youtube_enabled') == 'true',
            youtube_title=data.get('youtube_title'),
            youtube_description=data.get('youtube_description'),
            youtube_tags=data.get('youtube_tags'),
            instagram_enabled=data.get('instagram_enabled') == 'true',
            instagram_caption=data.get('instagram_caption'),
            tiktok_enabled=data.get('tiktok_enabled') == 'true',
            tiktok_caption=data.get('tiktok_caption'),
            vk_enabled=data.get('vk_enabled') == 'true',
            vk_caption=data.get('vk_caption'),
            schedule_type=data.get('schedule_type', 'now'),
            scheduled_time=datetime.fromisoformat(data.get('scheduled_time')) if data.get('scheduled_time') else None,
            timezone=data.get('timezone'),
            status='pending'
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Пост создан! (Публикация будет на следующем этапе)',
            'post_id': post.id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'}), 400

@app.route('/connect/<platform>')
def connect_platform(platform):
    flash(f'Подключение {platform} будет реализовано на следующем этапе', 'info')
    return redirect(url_for('settings'))

@app.route('/disconnect/<platform>')
def disconnect_platform(platform):
    user = get_default_user()
    account = SocialAccount.query.filter_by(user_id=user.id, platform=platform).first()
    if account:
        account.is_active = False
        db.session.commit()
        flash(f'{platform.capitalize()} отключён', 'success')
    return redirect(url_for('settings'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Создаём дефолтного пользователя при первом запуске
        get_default_user()
    app.run(debug=True, host='0.0.0.0', port=5000)
