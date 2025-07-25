from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, SubmitField, HiddenField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, NumberRange, Optional

class TournamentCreationForm(FlaskForm):
    name = StringField('Tournament Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    entry_fee = FloatField('Entry Fee', default=0, validators=[DataRequired(), NumberRange(min=0)])
    max_participants = IntegerField('Max Participants', validators=[DataRequired(), NumberRange(min=2, message='Must be at least 2 participants.')])
    prize_places = SelectField('Number of Prize Places', choices=[(1, '1'), (2, '2'), (3, '3')], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Next: Select Matches')

class PredictionForm(FlaskForm):
    home_score = IntegerField('Home', validators=[Optional()])
    away_score = IntegerField('Away', validators=[Optional()])
    match_id = HiddenField('Match ID')
    submit = SubmitField('Save')