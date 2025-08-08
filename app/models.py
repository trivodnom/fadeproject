from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func # <-- Добавьте этот импорт вверху файла


participants = db.Table('participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('tournament_id', db.Integer, db.ForeignKey('tournament.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(10), default='user')
    balance = db.Column(db.Float, default=0.0)
    avatar = db.Column(db.String(120), nullable=True, default='default.jpg')
    # ДОБАВЬТЕ ЭТУ СТРОКУ
    join_date = db.Column(db.DateTime, server_default=func.now())


    # ЯВНО УКАЗЫВАЕМ СВЯЗЬ
    tournaments = db.relationship('Tournament', secondary=participants, back_populates='attendees')
    predictions = db.relationship('Prediction', back_populates='user', lazy='dynamic')
    balance_history = db.relationship('BalanceHistory', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=True)
    entry_fee = db.Column(db.Float, nullable=False, default=0.0)
    start_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, index=True) # <-- ДОБАВИТЬ ЭТУ СТРОКУ
    status = db.Column(db.String(20), default='upcoming') # upcoming, active, finished, cancelled
    max_participants = db.Column(db.Integer, nullable=True)
    prize_places = db.Column(db.Integer, default=1)
    manual_results = db.Column(db.Boolean, default=False)
    league_id = db.Column(db.Integer, nullable=True) # <-- Это поле можно удалить или оставить, оно больше не главное
    matches_json = db.Column(db.Text, nullable=True)
    sport = db.Column(db.String(50), nullable=False, default='football')

    # ЯВНО УКАЗЫВАЕМ ОБРАТНУЮ СВЯЗЬ
    attendees = db.relationship('User', secondary=participants, back_populates='tournaments')
    predictions = db.relationship('Prediction', back_populates='tournament', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Tournament {self.name}>'

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    match_id = db.Column(db.String(50), nullable=False)
    home_team = db.Column(db.String(100))
    away_team = db.Column(db.String(100))
    match_date = db.Column(db.DateTime)
    home_score_prediction = db.Column(db.Integer)
    away_score_prediction = db.Column(db.Integer)
    home_score_actual = db.Column(db.Integer)
    away_score_actual = db.Column(db.Integer)
    points_awarded = db.Column(db.Integer, default=0)

    # ЯВНО УКАЗЫВАЕМ СВЯЗИ
    user = db.relationship('User', back_populates='predictions')
    tournament = db.relationship('Tournament', back_populates='predictions')

    __table_args__ = (db.UniqueConstraint('user_id', 'tournament_id', 'match_id', name='_user_tournament_match_uc'),)

    def __repr__(self):
        return f'<Prediction for match {self.match_id} by {self.user.username} in {self.tournament.name}>'

class BalanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    change_amount = db.Column(db.Float, nullable=False)
    new_balance = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    user = db.relationship('User', back_populates='balance_history')

    def __repr__(self):
        return f'<BalanceHistory for {self.user.username}: {self.change_amount}>'