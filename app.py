from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///social_poster.db').replace('postgres://', 'postgresql://')
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

# Инициализация базы
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Ошибка создания БД: {e}")

# Обработчик ошибок
@app.errorhandler(500)
def internal_error(error):
    return f"<h1>Ошибка сервера</h1><pre>{traceback.format_exc()}</pre>", 500

@app.errorhandler(Exception)
def handle_exception(e):
    return f"<h1>Ошибка</h1><pre>{str(e)}\n{traceback.format_exc()}</pre>", 500

# Маршруты
@app.route('/')
def index():
    try:
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Ошибка: {str(e)}<pre>{traceback.format_exc()}</pre>", 500

@app.route('/dashboard')
def dashboard():
    try:
        connected = {
            'youtube': SocialAccount.query.filter_by(platform='youtube', is_active=True).first(),
            'instagram': SocialAccount.query.filter_by(platform='instagram', is_active=True).first(),
            'tiktok': SocialAccount.query.filter_by(platform='tiktok', is_active=True).first(),
            'vk': SocialAccount.query.filter_by(platform='vk', is_active=True).first(),
        }
        user = {'name': 'Admin', 'email': 'admin@local'}
        return render_template('dashboard.html', connected=connected, user=user)
    except Exception as e:
        return f"Ошибка dashboard: {str(e)}<pre>{traceback.format_exc()}</pre>", 500

@app.route('/settings')
def settings():
    try:
        platforms = {
            'youtube': SocialAccount.query.filter_by(platform='youtube', is_active=True).first(),
            'instagram': SocialAccount.query.filter_by(platform='instagram', is_active=True).first(),
            'tiktok': SocialAccount.query.filter_by(platform='tiktok', is_active=True).first(),
            'vk': SocialAccount.query.filter_by(platform='vk', is_active=True).first(),
        }
        user = {'name': 'Admin', 'email': 'admin@local'}
        return render_template('settings.html', platforms=platforms, user=user)
    except Exception as e:
        return f"Ошибка settings: {str(e)}<pre>{traceback.format_exc()}</pre>", 500

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
    try:
        account = SocialAccount.query.filter_by(platform=platform, is_active=True).first()
        if account:
            account.is_active = False
            db.session.commit()
            flash(f'{platform.capitalize()} отключён', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
