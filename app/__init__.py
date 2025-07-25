from flask import Flask, redirect, url_for, request
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, TextAreaField, IntegerField
from wtforms.fields import DateTimeField
from sqlalchemy.orm.attributes import get_history
from flask_wtf.csrf import CSRFProtect
from flask_admin.contrib.sqla.fields import QuerySelectField

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'
admin = Admin(name='FadeProject Admin', template_mode='bootstrap3')
csrf = CSRFProtect()

class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

class UserEditForm(FlaskForm):
    username = StringField('Username')
    email = StringField('Email')
    role = SelectField('Role', choices=[('user', 'User'), ('organizer', 'Organizer'), ('admin', 'Admin')])
    balance = FloatField('Balance')

class TournamentEditForm(FlaskForm):
    name = StringField('Name')
    description = TextAreaField('Description')
    entry_fee = FloatField('Entry Fee')
    prize_pool = FloatField('Prize Pool')
    start_date = DateTimeField('Start Date', format='%Y-%m-%d %H:%M:%S', render_kw={"placeholder": "YYYY-MM-DD HH:MM:SS"})
    end_date = DateTimeField('End Date', format='%Y-%m-%d %H:%M:%S', render_kw={"placeholder": "YYYY-MM-DD HH:MM:SS"})
    status = SelectField('Status', choices=[('open', 'Open'), ('active', 'Active'), ('finished', 'Finished'), ('cancelled', 'Cancelled')])
    max_participants = IntegerField('Max Participants')
    prize_places = IntegerField('Prize Places')

class PredictionEditForm(FlaskForm):
    pass # Will be defined dynamically

class UserAdminView(MyModelView):
    form = UserEditForm
    column_list = ('username', 'email', 'role', 'balance')
    column_searchable_list = ('username', 'email')
    column_filters = ('role',)

    def on_model_change(self, form, model, is_created):
        from app.models import BalanceHistory
        if not is_created:
            balance_history = get_history(model, 'balance')
            if balance_history.has_changes():
                old_balance = balance_history.deleted[0] if balance_history.deleted else 0
                new_balance = balance_history.added[0] if balance_history.added else old_balance
                amount_changed = new_balance - old_balance
                if amount_changed != 0:
                    history_entry = BalanceHistory(user_id=model.id, amount=amount_changed, description="Admin adjustment")
                    db.session.add(history_entry)
        super(UserAdminView, self).on_model_change(form, model, is_created)

class TournamentAdminView(MyModelView):
    form = TournamentEditForm
    column_list = ('name', 'entry_fee', 'prize_pool', 'start_date', 'status')

class PredictionAdminView(MyModelView):
    form_columns = ('home_score_prediction', 'away_score_prediction', 'points_awarded')
    column_list = ('user', 'tournament', 'match_id', 'home_score_prediction', 'away_score_prediction', 'points_awarded')
    column_filters = ('tournament', 'user')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    admin.init_app(app)
    csrf.init_app(app)

    from app.models import User, Tournament, Prediction
    from app.util import format_datetime_filter

    @app.context_processor
    def inject_utility_processor():
        import dateutil.parser
        from datetime import datetime, timezone
        return dict(dateutil=dateutil, datetime=datetime, timezone=timezone)
        
    app.jinja_env.filters['format_datetime'] = format_datetime_filter

    from app.routes import main_bp
    app.register_blueprint(main_bp)
    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.user import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    from app.tournament import tournament_bp
    app.register_blueprint(tournament_bp, url_prefix='/tournaments')

    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(TournamentAdminView(Tournament, db.session))
    admin.add_view(PredictionAdminView(Prediction, db.session))

    return app