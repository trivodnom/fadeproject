import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- НОВЫЕ ПЕРЕМЕННЫЕ ---
    API_HOST = os.environ.get('API_HOST') or 'v3.football.api-sports.io'
    API_KEY = os.environ.get('API_KEY') or '20244b21779b98fc5ea2bdcd18680816'