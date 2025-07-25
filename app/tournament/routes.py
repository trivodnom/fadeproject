import json
from datetime import datetime
import dateutil.parser
from flask import render_template, abort, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.tournament import tournament_bp
from app.tournament.forms import TournamentCreationForm, PredictionForm
from app.decorators import admin_or_organizer_required
from app.models import Tournament, BalanceHistory, Prediction, User
from app.api_client import get_matches_for_league, LEAGUES

@tournament_bp.route('/')
def list_tournaments():
    tournaments = Tournament.query.filter(Tournament.status != 'draft').order_by(Tournament.start_date.asc()).all()
    return render_template('tournament/list.html', tournaments=tournaments, title='Tournaments')

@tournament_bp.route('/<int:tournament_id>')
def tournament_details(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)

    matches_to_render = []
    if tournament.matches:
        try:
            matches_to_render = json.loads(tournament.matches)
        except (json.JSONDecodeError, TypeError):
            flash('Could not parse match data for this tournament.', 'warning')

    form = PredictionForm()

    user_predictions = {}
    if current_user.is_authenticated:
        predictions = Prediction.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).all()
        for p in predictions:
            user_predictions[p.match_id] = p

    leaderboard = db.session.query(
        User.username,
        db.func.sum(Prediction.points_awarded).label('total_points')
    ).join(Prediction, User.id == Prediction.user_id)\
     .filter(Prediction.tournament_id == tournament.id)\
     .group_by(User.username)\
     .order_by(db.desc('total_points')).all()

    return render_template('tournament/details.html',
                           tournament=tournament,
                           matches=matches_to_render,
                           title=tournament.name,
                           form=form,
                           user_predictions=user_predictions,
                           leaderboard=leaderboard)

@tournament_bp.route('/<int:tournament_id>/predict', methods=['POST'])
@login_required
def make_prediction(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)

    match_id_str = request.form.get('match_id')
    if not match_id_str:
        flash('Match ID was not provided.', 'danger')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

    match_id = int(match_id_str)
    home_score = request.form.get('home_score')
    away_score = request.form.get('away_score')

    prediction = Prediction.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id,
        match_id=match_id
    ).first()

    if prediction:
        prediction.home_score_prediction = home_score
        prediction.away_score_prediction = away_score
    else:
        all_matches_info = json.loads(tournament.matches)
        match_info = next((m for m in all_matches_info if m['fixture']['id'] == match_id), None)

        if match_info:
            new_prediction = Prediction(
                user_id=current_user.id,
                tournament_id=tournament.id,
                match_id=match_id,
                match_date=dateutil.parser.isoparse(match_info['fixture']['date']),
                home_team_name=match_info['teams']['home']['name'],
                home_team_logo=match_info['teams']['home']['logo'],
                away_team_name=match_info['teams']['away']['name'],
                away_team_logo=match_info['teams']['away']['logo'],
                home_score_prediction=home_score,
                away_score_prediction=away_score
            )
            db.session.add(new_prediction)
        else:
            flash('Could not find match info to create prediction.', 'danger')

    db.session.commit()
    flash('Your prediction has been saved!', 'success')
    return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

@tournament_bp.route('/<int:tournament_id>/action', methods=['POST'])
@login_required
def join_or_leave_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    action = request.form.get('action')

    if action == 'join':
        if current_user.balance < tournament.entry_fee:
            flash('You do not have enough funds to join this tournament.', 'danger')
        elif tournament in current_user.tournaments:
            flash('You are already in this tournament.', 'info')
        else:
            current_user.balance -= tournament.entry_fee
            history_entry = BalanceHistory(user_id=current_user.id, amount=-tournament.entry_fee, description=f'Entry fee for {tournament.name}')
            db.session.add(history_entry)
            tournament.attendees.append(current_user)
            db.session.commit()
            flash(f'You have successfully joined the tournament: {tournament.name}!', 'success')

    elif action == 'leave':
        if tournament.status != 'open':
            flash('You cannot leave a tournament that has already started.', 'danger')
        elif tournament not in current_user.tournaments:
            flash('You are not in this tournament.', 'info')
        else:
            current_user.balance += tournament.entry_fee
            history_entry = BalanceHistory(user_id=current_user.id, amount=tournament.entry_fee, description=f'Refund for leaving {tournament.name}')
            db.session.add(history_entry)
            tournament.attendees.remove(current_user)
            Prediction.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).delete()
            db.session.commit()
            flash(f'You have left the tournament: {tournament.name}.', 'success')

    return redirect(request.referrer or url_for('tournaments.tournament_details', tournament_id=tournament.id))

@tournament_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_or_organizer_required
def create_tournament():
    form = TournamentCreationForm()
    if form.validate_on_submit():
        new_tournament = Tournament(
            name=form.name.data,
            description=form.description.data,
            entry_fee=form.entry_fee.data,
            max_participants=form.max_participants.data,
            prize_places=form.prize_places.data,
            status='draft'
        )
        db.session.add(new_tournament)
        db.session.commit()
        return redirect(url_for('tournaments.select_matches', tournament_id=new_tournament.id))

    return render_template('tournament/create_step1.html', title='Create Tournament - Step 1', form=form)

@tournament_bp.route('/<int:tournament_id>/select_matches', methods=['GET', 'POST'])
@login_required
@admin_or_organizer_required
def select_matches(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)

    if request.method == 'POST':
        matches_data_json = request.form.get('selected_matches_json')
        if not matches_data_json or matches_data_json == '[]':
            flash('Please select at least one match.', 'warning')
            return redirect(url_for('tournaments.select_matches', tournament_id=tournament.id))

        matches_data = json.loads(matches_data_json)

        match_dates = [dateutil.parser.isoparse(item['fixture']['date']) for item in matches_data]

        tournament.matches = matches_data_json
        tournament.start_date = min(match_dates)
        tournament.end_date = max(match_dates)
        tournament.status = 'open'
        db.session.commit()

        flash('Tournament has been successfully created!', 'success')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

    return render_template('tournament/create_step2.html',
                           title='Select Matches',
                           tournament=tournament,
                           leagues=LEAGUES)

@tournament_bp.route('/get_matches/<int:league_id>')
@login_required
@admin_or_organizer_required
def get_matches_by_league_id(league_id):
    matches = get_matches_for_league(league_id)
    if matches is None:
        return jsonify({'error': 'Failed to retrieve matches from API'}), 500
    return jsonify(matches)