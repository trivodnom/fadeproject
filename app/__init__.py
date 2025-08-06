from flask import Flask, redirect, url_for, request, flash
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, TextAreaField, IntegerField
from sqlalchemy.orm.attributes import get_history
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
from flask_babel import Babel

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'
admin = Admin(name='FadeProject Admin', template_mode='bootstrap3')
csrf = CSRFProtect()
babel = Babel()

class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

class UserAdminView(MyModelView):
    # Убираем form = AdminUserEditForm отсюда
    form_columns = ('username', 'email', 'role', 'balance')
    column_list = ('username', 'email', 'role', 'balance')

    # Переопределяем метод, чтобы задать форму динамически
    def edit_form(self, obj=None):
        from app.user.forms import AdminUserEditForm # <-- Импортируем здесь!
        return AdminUserEditForm(obj=obj)


class TournamentAdminView(MyModelView):
    column_list = ('name', 'entry_fee', 'start_date', 'status', 'manage_link')
    form_columns = ('name', 'description', 'entry_fee', 'status', 'max_participants', 'prize_places')

    def _format_manage_link(view, context, model, name):
        manage_url = url_for('tournaments.manage_tournament', tournament_id=model.id)
        return Markup(f'<a href="{manage_url}" class="btn btn-primary">Manage Scores</a>')

    column_formatters = {
        'manage_link': _format_manage_link
    }

    def on_model_delete(self, model):
        from app.models import BalanceHistory
        try:
            for user in model.attendees:
                user.balance += model.entry_fee
                history_entry = BalanceHistory(
                    user_id=user.id,
                    change_amount=model.entry_fee,
                    new_balance=user.balance,
                    description=f"Refund for cancelled/deleted tournament: {model.name}"
                )
                db.session.add(history_entry)

            flash(f"Refunds have been processed for all {len(model.attendees)} participants of the deleted tournament '{model.name}'.", 'success')

        except Exception as e:
            if not self.handle_view_exception(e):
                flash(f'Failed to process refunds: {e}', 'error')
            db.session.rollback()
            return False

        return super(TournamentAdminView, self).on_model_delete(model)

class PredictionAdminView(MyModelView):
    can_edit = True
    form_columns = ('home_score_actual', 'away_score_actual', 'points_awarded')
    column_list = ('user', 'tournament', 'match_id', 'home_score_prediction', 'away_score_prediction', 'home_score_actual', 'away_score_actual', 'points_awarded')
    column_filters = ('tournament', 'user')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.jinja_env.add_extension('jinja2.ext.do')
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    admin.init_app(app)
    csrf.init_app(app)
    babel.init_app(app)

    from app.models import User, Tournament, Prediction
    from app.util import format_datetime_filter

    app.jinja_env.filters['format_datetime'] = format_datetime_filter

    @app.context_processor
    def inject_utility_processor():
        import dateutil.parser
        from datetime import datetime, timezone
        return dict(dateutil=dateutil, datetime=datetime, timezone=timezone)

    from app.routes import main_bp
    app.register_blueprint(main_bp)
    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.user import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    from app.tournament import tournament_bp
    app.register_blueprint(tournament_bp, url_prefix='/tournaments')

    admin.add_view(TournamentAdminView(Tournament, db.session, name='Tournaments'))
    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(PredictionAdminView(Prediction, db.session))

    return app