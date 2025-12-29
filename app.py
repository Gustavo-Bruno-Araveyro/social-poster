from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import traceback
import requests
import secrets
from urllib.parse import urlencode

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///social_poster.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Конфигурация YouTube OAuth
YOUTUBE_CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID')
YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET')
YOUTUBE_REDIRECT_URI = os.environ.get('YOUTUBE_REDIRECT_URI', 'https://web-production-e92c4.up.railway.app/authorize/youtube')

# Модели
class SocialAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    platform_username = db.Column(db.String(200))
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    platform_user_id = db.Column(db.String(200))

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

# YouTube OAuth
@app.route('/connect/youtube')
def connect_youtube():
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        flash('YouTube OAuth не настроен. Добавьте YOUTUBE_CLIENT_ID и YOUTUBE_CLIENT_SECRET в Railway Variables.', 'error')
        return redirect(url_for('settings'))
    
    # Генерируем state для безопасности
    state = secrets.token_urlsafe(32)
    session['youtube_oauth_state'] = state
    
    # Параметры для OAuth запроса
    params = {
        'client_id': YOUTUBE_CLIENT_ID,
        'redirect_uri': YOUTUBE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly',
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(auth_url)

@app.route('/authorize/youtube')
def authorize_youtube():
    try:
        # Проверяем state
        state = request.args.get('state')
        if not state or state != session.get('youtube_oauth_state'):
            flash('Ошибка безопасности при авторизации', 'error')
            return redirect(url_for('settings'))
        
        code = request.args.get('code')
        if not code:
            error = request.args.get('error', 'Неизвестная ошибка')
            flash(f'Ошибка авторизации: {error}', 'error')
            return redirect(url_for('settings'))
        
        # Обмениваем код на токен
        token_data = {
            'code': code,
            'client_id': YOUTUBE_CLIENT_ID,
            'client_secret': YOUTUBE_CLIENT_SECRET,
            'redirect_uri': YOUTUBE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Получаем информацию о канале
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        channel_response = requests.get(
            'https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
            headers=headers
        )
        
        if channel_response.status_code == 200:
            channel_data = channel_response.json()
            if channel_data.get('items'):
                channel = channel_data['items'][0]
                channel_title = channel['snippet']['title']
                channel_id = channel['id']
            else:
                channel_title = 'YouTube канал'
                channel_id = None
        else:
            channel_title = 'YouTube канал'
            channel_id = None
        
        # Сохраняем или обновляем аккаунт
        account = SocialAccount.query.filter_by(platform='youtube').first()
        if account:
            account.is_active = True
            account.access_token = tokens['access_token']
            account.refresh_token = tokens.get('refresh_token')
            account.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
            account.platform_username = channel_title
            account.platform_user_id = channel_id
        else:
            account = SocialAccount(
                platform='youtube',
                is_active=True,
                access_token=tokens['access_token'],
                refresh_token=tokens.get('refresh_token'),
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600)),
                platform_username=channel_title,
                platform_user_id=channel_id
            )
            db.session.add(account)
        
        db.session.commit()
        flash('YouTube успешно подключён!', 'success')
        return redirect(url_for('settings'))
        
    except Exception as e:
        flash(f'Ошибка подключения YouTube: {str(e)}', 'error')
        return redirect(url_for('settings'))

@app.route('/connect/instagram')
def connect_instagram():
    flash('Подключение Instagram будет реализовано позже', 'info')
    return redirect(url_for('settings'))

@app.route('/connect/tiktok')
def connect_tiktok():
    flash('Подключение TikTok будет реализовано позже', 'info')
    return redirect(url_for('settings'))

@app.route('/connect/vk')
def connect_vk():
    flash('Подключение VK будет реализовано позже', 'info')
    return redirect(url_for('settings'))

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
