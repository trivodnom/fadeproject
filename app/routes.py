from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app
from flask_login import current_user, login_required
from sqlalchemy import func
from app import db
from app.models import Tournament, User, participants, BalanceHistory
import json
import os
import requests
from app.api_client import get_team_logo_url


main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    return redirect(url_for('tournaments.list_tournaments'))

# ===== НОВЫЙ РОУТ ДЛЯ КЭШИРОВАНИЯ ЛОГОТИПОВ =====
@main_bp.route('/image/team_logo/<int:team_id>')
def get_team_logo(team_id):
    # Определяем путь к папке с кэшем логотипов
    logo_cache_dir = os.path.join(current_app.static_folder, 'uploads', 'team_logos')
    # Имя файла будет основано на ID команды. Используем .png для единообразия.
    logo_filename = f"{team_id}.png"
    logo_path = os.path.join(logo_cache_dir, logo_filename)

    # 1. Если файл уже есть в кэше, отдаем его
    if os.path.exists(logo_path):
        return send_from_directory(logo_cache_dir, logo_filename)

    # 2. Если файла нет, получаем URL логотипа через API
    logo_url = get_team_logo_url(team_id)
    
    # Заглушка, если URL не найден
    placeholder_dir = os.path.join(current_app.static_folder, 'img')
    if not logo_url:
        return send_from_directory(placeholder_dir, 'default-avatar.png')

    # 3. Скачиваем логотип
    try:
        res = requests.get(logo_url, stream=True, timeout=10)
        res.raise_for_status()

        # Создаем папку для кэша, если ее нет
        os.makedirs(logo_cache_dir, exist_ok=True)

        # Сохраняем логотип в файл
        with open(logo_path, 'wb') as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)

        # 4. Отдаем свежескачанный файл
        return send_from_directory(logo_cache_dir, logo_filename)

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to download logo for team {team_id} from {logo_url}: {e}")
        # В случае ошибки отдаем заглушку
        return send_from_directory(placeholder_dir, 'default-avatar.png')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_authenticated and current_user.role == 'admin':
        # --- Статистика для карточек ---
        total_tournaments = Tournament.query.count()
        active_tournaments = Tournament.query.filter(Tournament.status.in_(['active', 'open'])).count()
        total_users = User.query.count()

        total_turnover_query = db.session.query(func.sum(Tournament.entry_fee))\
            .join(participants, participants.c.tournament_id == Tournament.id)\
            .scalar()
        total_turnover = total_turnover_query or 0
        platform_earnings = total_turnover * 0.10

        stats = {
            'total_tournaments': total_tournaments,
            'active_tournaments': active_tournaments,
            'total_users': total_users,
            'platform_earnings': platform_earnings
        }

        # --- Данные для графиков ---
        user_reg_data = db.session.query(
                func.count(User.id),
                func.strftime('%Y-%m-%d', User.join_date)
            ).group_by(func.strftime('%Y-%m-%d', User.join_date))\
             .order_by(func.strftime('%Y-%m-%d', User.join_date).asc()).all()

        user_chart_labels = [d for c, d in user_reg_data]
        user_chart_values = [c for c, d in user_reg_data]
        
        daily_earnings_data = db.session.query(
                func.strftime('%Y-%m-%d', BalanceHistory.timestamp),
                func.sum(BalanceHistory.change_amount * -0.1) # Сразу считаем 10% от списания
            ).filter(BalanceHistory.description.like('Entry fee%'))\
             .group_by(func.strftime('%Y-%m-%d', BalanceHistory.timestamp))\
             .order_by(func.strftime('%Y-%m-%d', BalanceHistory.timestamp).asc()).all()

        earnings_chart_labels = [date_str for date_str, daily_total in daily_earnings_data]
        earnings_chart_values = [float(daily_total) if daily_total is not None else 0 for date_str, daily_total in daily_earnings_data]

        chart_data = {
            'user_labels': json.dumps(user_chart_labels),
            'user_values': json.dumps(user_chart_values),
            'earnings_labels': json.dumps(earnings_chart_labels),
            'earnings_values': json.dumps(earnings_chart_values)
        }

        latest_tournaments = Tournament.query.order_by(Tournament.id.desc()).limit(5).all()

        return render_template("admin_dashboard.html",
                               title='Admin Dashboard',
                               stats=stats,
                               chart_data=chart_data,
                               tournaments=latest_tournaments)

    return redirect(url_for('tournaments.list_tournaments'))