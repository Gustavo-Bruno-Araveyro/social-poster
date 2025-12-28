from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (для локальной разработки)
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social_poster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# OAuth настройки
oauth = OAuth(app)

# Google OAuth
# Отладочный вывод - показываем ВСЕ переменные окружения
print("=" * 50)
print("🔍 ВСЕ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ:")
for key, value in sorted(os.environ.items()):
    if 'GOOGLE' in key or 'SECRET' in key:
        print(f"  {key} = {value}")
print("=" * 50)

google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')

# Отладочный вывод
if not google_client_id:
    print("⚠️ WARNING: GOOGLE_CLIENT_ID не установлен!")
    print(f"   Проверка os.environ: {list(os.environ.keys())}")
else:
    print(f"✅ GOOGLE_CLIENT_ID загружен: {google_client_id[:20]}...")
if not google_client_secret:
    print("⚠️ WARNING: GOOGLE_CLIENT_SECRET не установлен!")
else:
    print(f"✅ GOOGLE_CLIENT_SECRET загружен: {google_client_secret[:10]}...")

# Регистрируем OAuth только если переменные загружены
if google_client_id and google_client_secret:
    google = oauth.register(
        name='google',
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
else:
    print("❌ ОШИБКА: OAuth не зарегистрирован из-за отсутствия переменных!")
    google = None

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
    
    # Связи с соцсетями
    social_accounts = db.relationship('SocialAccount', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)

class SocialAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # youtube, instagram, tiktok, vk
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
    
    # Контент
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(50))  # video, image
    
    # YouTube
    youtube_enabled = db.Column(db.Boolean, default=False)
    youtube_title = db.Column(db.String(100))
    youtube_description = db.Column(db.Text)
    youtube_tags = db.Column(db.String(500))
    youtube_status = db.Column(db.String(50))  # pending, published, failed
    youtube_video_id = db.Column(db.String(100))
    
    # Instagram
    instagram_enabled = db.Column(db.Boolean, default=False)
    instagram_caption = db.Column(db.Text)
    instagram_status = db.Column(db.String(50))
    instagram_post_id = db.Column(db.String(100))
    
    # TikTok
    tiktok_enabled = db.Column(db.Boolean, default=False)
    tiktok_caption = db.Column(db.Text)
    tiktok_status = db.Column(db.String(50))
    tiktok_video_id = db.Column(db.String(100))
    
    # VK
    vk_enabled = db.Column(db.Boolean, default=False)
    vk_caption = db.Column(db.Text)
    vk_status = db.Column(db.String(50))
    vk_post_id = db.Column(db.String(100))
    
    # Расписание
    schedule_type = db.Column(db.String(20), default='now')  # now, scheduled
    scheduled_time = db.Column(db.DateTime)
    timezone = db.Column(db.String(20))
    
    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='draft')  # draft, publishing, published, failed

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# МАРШРУТЫ - АВТОРИЗАЦИЯ
# =========================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login/google')
def login_google():
    # Проверяем, что OAuth зарегистрирован
    if not google or not google_client_id or not google_client_secret:
        flash('Ошибка конфигурации OAuth. Обратитесь к администратору.', 'error')
        return redirect(url_for('login'))
    
    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    try:
        token = google.authorize_access_token()
        
        # Получаем информацию о пользователе из ID токена или через userinfo endpoint
        resp = google.get('userinfo', token=token)
        resp.raise_for_status()
        user_info = resp.json()
        
        if user_info and 'sub' in user_info:
            user = User.query.filter_by(google_id=user_info['sub']).first()
            
            if not user:
                # Создаём нового пользователя
                user = User(
                    email=user_info.get('email'),
                    name=user_info.get('name'),
                    google_id=user_info['sub']
                )
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            flash('Успешный вход!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Не удалось получить данные пользователя', 'error')
    except Exception as e:
        flash(f'Ошибка авторизации: {str(e)}', 'error')
    
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# =========================
# МАРШРУТЫ - ОСНОВНЫЕ
# =========================

@app.route('/dashboard')
@login_required
def dashboard():
    # Получаем подключённые соцсети
    connected_platforms = {
        'youtube': SocialAccount.query.filter_by(user_id=current_user.id, platform='youtube', is_active=True).first(),
        'instagram': SocialAccount.query.filter_by(user_id=current_user.id, platform='instagram', is_active=True).first(),
        'tiktok': SocialAccount.query.filter_by(user_id=current_user.id, platform='tiktok', is_active=True).first(),
        'vk': SocialAccount.query.filter_by(user_id=current_user.id, platform='vk', is_active=True).first(),
    }
    return render_template('dashboard.html', connected=connected_platforms, user=current_user)

@app.route('/settings')
@login_required
def settings():
    social_accounts = SocialAccount.query.filter_by(user_id=current_user.id).all()
    platforms_status = {
        'youtube': False,
        'instagram': False,
        'tiktok': False,
        'vk': False
    }
    for account in social_accounts:
        if account.is_active:
            platforms_status[account.platform] = account
    
    return render_template('settings.html', platforms=platforms_status, user=current_user)

# =========================
# API - ПУБЛИКАЦИЯ ПОСТОВ
# =========================

@app.route('/api/publish', methods=['POST'])
@login_required
def publish_post():
    try:
        data = request.form
        file = request.files.get('video')
        
        # Создаём запись поста
        post = Post(
            user_id=current_user.id,
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
        
        # Сохраняем файл (упрощённо, в продакшене нужно облако)
        if file:
            # TODO: Сохранение файла и загрузка в соцсети
            pass
        
        db.session.add(post)
        db.session.commit()
        
        # TODO: Здесь будет логика публикации в соцсети
        # Пока возвращаем успех
        
        return jsonify({
            'success': True,
            'message': 'Пост успешно создан! (Публикация в соцсети будет подключена на следующем этапе)',
            'post_id': post.id
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        }), 400

# =========================
# API - ПОДКЛЮЧЕНИЕ СОЦСЕТЕЙ
# =========================

@app.route('/connect/youtube')
@login_required
def connect_youtube():
    # TODO: OAuth для YouTube
    flash('Подключение YouTube будет реализовано на следующем этапе', 'info')
    return redirect(url_for('settings'))

@app.route('/connect/instagram')
@login_required
def connect_instagram():
    # TODO: OAuth для Instagram
    flash('Подключение Instagram будет реализовано на следующем этапе', 'info')
    return redirect(url_for('settings'))

@app.route('/connect/tiktok')
@login_required
def connect_tiktok():
    # TODO: OAuth для TikTok
    flash('Подключение TikTok будет реализовано на следующем этапе', 'info')
    return redirect(url_for('settings'))

@app.route('/connect/vk')
@login_required
def connect_vk():
    # TODO: OAuth для VK
    flash('Подключение VK будет реализовано на следующем этапе', 'info')
    return redirect(url_for('settings'))

@app.route('/disconnect/<platform>')
@login_required
def disconnect_platform(platform):
    account = SocialAccount.query.filter_by(
        user_id=current_user.id,
        platform=platform
    ).first()
    
    if account:
        account.is_active = False
        db.session.commit()
        flash(f'{platform.capitalize()} отключён', 'success')
    
    return redirect(url_for('settings'))

# =========================
# ИНИЦИАЛИЗАЦИЯ
# =========================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаём таблицы при первом запуске
    app.run(debug=True, host='0.0.0.0', port=5000)