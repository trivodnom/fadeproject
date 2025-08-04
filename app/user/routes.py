import os
from werkzeug.utils import secure_filename
from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from app import db
from app.user import user_bp
from app.user.forms import EditProfileForm
from app.models import BalanceHistory, User

def save_picture(form_picture):
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/avatars', picture_fn)
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    form_picture.save(picture_path)
    return picture_fn

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = EditProfileForm(original_username=current_user.username, original_email=current_user.email)
    if form.validate_on_submit():
        if form.avatar.data:
            if current_user.avatar and current_user.avatar != 'default.jpg':
                old_avatar_path = os.path.join(current_app.root_path, 'static/avatars', current_user.avatar)
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)
            picture_file = save_picture(form.avatar.data)
            current_user.avatar = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('profile.profile'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    avatar_image = url_for('static', filename='avatars/' + (current_user.avatar or 'default.jpg'))
    history = BalanceHistory.query.filter_by(user_id=current_user.id).order_by(BalanceHistory.timestamp.desc()).all()

    return render_template('user/profile.html', title='Profile', form=form, history=history, avatar_image=avatar_image)

@user_bp.route('/delete_avatar', methods=['POST'])
@login_required
def delete_avatar():
    if current_user.avatar and current_user.avatar != 'default.jpg':
        avatar_path = os.path.join(current_app.root_path, 'static/avatars', current_user.avatar)
        if os.path.exists(avatar_path):
            os.remove(avatar_path)
        current_user.avatar = 'default.jpg'
        db.session.commit()
        flash('Your profile picture has been removed.', 'success')
    else:
        flash('You do not have a custom avatar to remove.', 'info')
    return redirect(url_for('profile.profile'))