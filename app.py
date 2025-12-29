from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social_poster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели
class SocialAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    platform_username = db.Column(db.String(200))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    youtube_enabled = db.Column(db.Boolean, default=False)
    youtube_title = db.Column(db.String(100))
    instagram_enabled = db.Column(db.Boolean, default=False)
    instagram_caption = db.Column(db.Text)
    tiktok_enabled = db.Column(db.Boolean, default=False)
    tiktok_caption = db.Column(db.Text)
    vk_enabled = db.Column(db.Boolean, default=False)
    vk_caption = db.Column(db.Text)
    status = db.Column(db.String(50), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Маршруты
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    connected = {
        'youtube': SocialAccount.query.filter_by(platform='youtube', is_active=True).first(),
        'instagram': SocialAccount.query.filter_by(platform='instagram', is_active=True).first(),
        'tiktok': SocialAccount.query.filter_by(platform='tiktok', is_active=True).first(),
        'vk': SocialAccount.query.filter_by(platform='vk', is_active=True).first(),
    }
    user = {'name': 'Admin', 'email': 'admin@local'}
    return render_template('dashboard.html', connected=connected, user=user)

@app.route('/settings')
def settings():
    platforms = {
        'youtube': SocialAccount.query.filter_by(platform='youtube', is_active=True).first(),
        'instagram': SocialAccount.query.filter_by(platform='instagram', is_active=True).first(),
        'tiktok': SocialAccount.query.filter_by(platform='tiktok', is_active=True).first(),
        'vk': SocialAccount.query.filter_by(platform='vk', is_active=True).first(),
    }
    user = {'name': 'Admin', 'email': 'admin@local'}
    return render_template('settings.html', platforms=platforms, user=user)

@app.route('/logout')
def logout():
    return redirect(url_for('dashboard'))

@app.route('/connect/<platform>')
def connect_platform(platform):
    flash(f'Подключение {platform} будет реализовано позже', 'info')
    return redirect(url_for('settings'))

@app.route('/connect/youtube')
def connect_youtube():
    return connect_platform('youtube')

@app.route('/connect/instagram')
def connect_instagram():
    return connect_platform('instagram')

@app.route('/connect/tiktok')
def connect_tiktok():
    return connect_platform('tiktok')

@app.route('/connect/vk')
def connect_vk():
    return connect_platform('vk')

@app.route('/disconnect/<platform>')
def disconnect_platform(platform):
    account = SocialAccount.query.filter_by(platform=platform, is_active=True).first()
    if account:
        account.is_active = False
        db.session.commit()
        flash(f'{platform.capitalize()} отключён', 'success')
    return redirect(url_for('settings'))

@app.route('/api/publish', methods=['POST'])
def publish_post():
    try:
        data = request.form
        post = Post(
            youtube_enabled=data.get('youtube_enabled') == 'true',
            youtube_title=data.get('youtube_title', ''),
            instagram_enabled=data.get('instagram_enabled') == 'true',
            instagram_caption=data.get('instagram_caption', ''),
            tiktok_enabled=data.get('tiktok_enabled') == 'true',
            tiktok_caption=data.get('tiktok_caption', ''),
            vk_enabled=data.get('vk_enabled') == 'true',
            vk_caption=data.get('vk_caption', ''),
            status='pending'
        )
        db.session.add(post)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Пост создан!', 'post_id': post.id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# Инициализация
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
