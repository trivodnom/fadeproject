from flask import Blueprint

user_bp = Blueprint('profile', __name__) # <--- ИЗМЕНЕНИЕ ЗДЕСЬ

from app.user import routes