import os
from datetime import timedelta # <-- ДОБАВЛЕН ИМПОРТ

# basedir нужен для построения абсолютных путей
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ===== НОВАЯ НАСТРОЙКА ДЛЯ "ЗАПОМНИТЬ МЕНЯ" =====
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    API_HOST = os.environ.get('API_HOST') or 'v3.football.api-sports.io'
    API_KEY = os.environ.get('API_KEY') or '20244b21779b98fc5ea2bdcd18680816'

    # Flask-Uploads ищет эту переменную, чтобы знать, куда сохранять файлы.
    # Имя переменной должно быть UPLOADED_{ИМЯ СЕТА}_DEST. У нас сет называется 'avatars'.
    UPLOADED_AVATARS_DEST = os.path.join(basedir, 'app', 'static', 'uploads', 'avatars')