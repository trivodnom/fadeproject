from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, SelectField
from wtforms.validators import DataRequired, Email, ValidationError
from app.models import User
from flask_login import current_user
from flask_wtf.file import FileField, FileAllowed


# Форма для редактирования профиля самим пользователем
class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    avatar = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Save Changes')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=self.username.data).first()
            if user:
                raise ValidationError('This username is already taken.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=self.email.data).first()
            if user:
                raise ValidationError('This email address is already registered.')

# Форма для редактирования пользователя в админке
class AdminUserEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    balance = FloatField('Balance')
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Admin')])