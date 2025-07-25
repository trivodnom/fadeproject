from flask import Blueprint

# Переименовали blueprint для избежания конфликтов
tournament_bp = Blueprint('tournaments', __name__)

from app.tournament import routes