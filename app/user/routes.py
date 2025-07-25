from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from app.user import user_bp
from app.user.forms import EditProfileForm
from app.models import BalanceHistory

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('profile.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    history = BalanceHistory.query.filter_by(user_id=current_user.id).order_by(BalanceHistory.timestamp.desc()).all()
    
    return render_template('user/profile.html', title='Profile', form=form, history=history)