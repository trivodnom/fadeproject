from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.profile import profile_bp
from app.profile.forms import EditProfileForm
from app.models import BalanceHistory
from app.extensions import avatars
import os

@profile_bp.route('/', methods=['GET', 'POST'])
@login_required
def profile():
    # ----- ИСПРАВЛЕНИЕ: ВОЗВРАЩАЕМ ИНИЦИАЛИЗАЦИЮ ФОРМЫ -----
    form = EditProfileForm(
        original_username=current_user.username,
        original_email=current_user.email,
        obj=current_user
    )
    
    if 'avatar' in request.files and request.files['avatar'].filename != '':
        if current_user.avatar:
            try:
                os.remove(os.path.join(current_app.config['UPLOADED_AVATARS_DEST'], current_user.avatar))
            except OSError as e:
                current_app.logger.error(f"Error deleting old avatar file: {e}")
        
        filename = avatars.save(request.files['avatar'])
        current_user.avatar = filename
        db.session.commit()
        flash('Your avatar has been updated.', 'success')
        return redirect(url_for('profile.profile'))

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile.profile'))
    
    if not form.is_submitted():
        form.username.data = current_user.username
        form.email.data = current_user.email

    page = request.args.get('page', 1, type=int)
    history_pagination = BalanceHistory.query.filter_by(user_id=current_user.id).order_by(BalanceHistory.timestamp.desc()).paginate(page=page, per_page=10, error_out=False)
    history_items = history_pagination.items

    return render_template(
        'profile/profile.html', 
        form=form, 
        history=history_items, 
        pagination=history_pagination,
        title='Profile'
    )


@profile_bp.route('/delete_avatar', methods=['POST'])
@login_required
def delete_avatar():
    if current_user.avatar:
        try:
            os.remove(os.path.join(current_app.config['UPLOADED_AVATARS_DEST'], current_user.avatar))
            current_user.avatar = None
            db.session.commit()
            flash('Your avatar has been deleted.', 'success')
        except OSError as e:
            flash(f'Error deleting avatar: {e}', 'danger')
    else:
        flash('You do not have a custom avatar to delete.', 'info')
    return redirect(url_for('profile.profile'))


@profile_bp.route('/load-more-history')
@login_required
def load_more_history():
    page = request.args.get('page', 2, type=int)
    pagination = BalanceHistory.query.filter_by(user_id=current_user.id).order_by(BalanceHistory.timestamp.desc()).paginate(page=page, per_page=10, error_out=False)
    history_items = pagination.items
    
    html = render_template('profile/history_rows.html', history=history_items)
    
    return jsonify({
        'html': html,
        'has_next': pagination.has_next
    })