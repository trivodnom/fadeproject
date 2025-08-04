from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from app import db
from app.models import Tournament, User, participants, BalanceHistory
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    return redirect(url_for('tournaments.list_tournaments'))

@main_bp.route('/dashboard')
@login_required # <-- Добавляем декоратор
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

        # --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ГРАФИКА ЗАРАБОТКА ---
        # Мы будем суммировать взносы, группируя по дате из BalanceHistory
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