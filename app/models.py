from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(10), default='user')
    balance = db.Column(db.Float, default=0.0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class BalanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('balance_history', lazy=True))

    def __repr__(self):
        return f'<BalanceHistory {self.description}>'

# --- НОВЫЕ МОДЕЛИ ---
participants = db.Table('participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('tournament_id', db.Integer, db.ForeignKey('tournament.id'), primary_key=True)
)

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    leagues = db.Column(db.String(200)) # Будем хранить ID лиг через запятую, например "39,140,78"
    matches = db.Column(db.Text) # Будем хранить ID матчей из API через запятую
    description = db.Column(db.Text)
    entry_fee = db.Column(db.Float, nullable=False, default=0)
    prize_pool = db.Column(db.Float, nullable=False, default=0)
    start_date = db.Column(db.DateTime, nullable=True) # Разрешаем быть пустым
    end_date = db.Column(db.DateTime, nullable=True)   # Разрешаем быть пустым
    status = db.Column(db.String(20), default='open')
    max_participants = db.Column(db.Integer)
    prize_places = db.Column(db.Integer, default=1)

    attendees = db.relationship(
        'User', secondary=participants,
        backref=db.backref('tournaments', lazy='dynamic'), lazy='dynamic'
    )

    def __repr__(self):
        return f'<Tournament {self.name}>'

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)

    # Match information saved from the API
    match_id = db.Column(db.Integer, nullable=False)
    match_date = db.Column(db.DateTime, nullable=False)
    home_team_name = db.Column(db.String(100))
    home_team_logo = db.Column(db.String(255))
    away_team_name = db.Column(db.String(100))
    away_team_logo = db.Column(db.String(255))

    # User's prediction
    home_score_prediction = db.Column(db.Integer)
    away_score_prediction = db.Column(db.Integer)

    # Result
    points_awarded = db.Column(db.Integer, default=0)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='predictions')
    tournament = db.relationship('Tournament', backref='predictions')

    # Unique prediction from one user for one match within a tournament
    __table_args__ = (db.UniqueConstraint('user_id', 'tournament_id', 'match_id', name='_user_tournament_match_uc'),)

    def __repr__(self):
        return f'<Prediction user:{self.user_id} match:{self.match_id}>'