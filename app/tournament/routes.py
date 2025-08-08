import json
from datetime import datetime, timezone
import dateutil.parser
from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, or_, and_, func, case
from app import db
from app.tournament import tournament_bp
from app.tournament.forms import TournamentCreationForm, PredictionForm
from app.decorators import admin_or_organizer_required
from app.models import Tournament, BalanceHistory, Prediction, User
from app.api_client import LEAGUES, get_matches_for_league, LEAGUE_STANDINGS_URLS
from app.tournament.utils import calculate_points, calculate_prize_distribution
from collections import defaultdict


# --- НОВАЯ ФУНКЦИЯ РАСПРЕДЕЛЕНИЯ ПРИЗОВ ---
def distribute_prizes_for_tournament(tournament):
    """
    Находит победителей, корректно обрабатывает ничьи и начисляет призы.
    """
    if not tournament.attendees:
        current_app.logger.info(f"Tournament {tournament.id}: No attendees, no prizes to distribute.")
        return

    leaderboard = db.session.query(
        User,
        func.sum(Prediction.points_awarded).label('total_points')
    ).join(Prediction).filter(
        Prediction.tournament_id == tournament.id
    ).group_by(User).order_by(
        db.desc('total_points')
    ).all()

    if not leaderboard:
        current_app.logger.info(f"Tournament {tournament.id}: No leaderboard data.")
        return

    scores_to_users = defaultdict(list)
    for user, points in leaderboard:
        score = points or 0
        scores_to_users[score].append(user)

    num_attendees = len(tournament.attendees)
    prize_map = calculate_prize_distribution(tournament, num_attendees, return_raw=True)

    if not prize_map:
        current_app.logger.warning(f"Tournament {tournament.id}: Prize distribution is not defined for {num_attendees} attendees.")
        return

    sorted_scores = sorted(scores_to_users.keys(), reverse=True)
    current_rank = 1

    for score in sorted_scores:
        winners = scores_to_users[score]
        num_winners_at_this_rank = len(winners)

        if current_rank > tournament.prize_places:
            break

        prizes_to_share = []
        for i in range(num_winners_at_this_rank):
            place = current_rank + i
            if place in prize_map:
                prizes_to_share.append(prize_map[place])

        if not prizes_to_share:
            current_rank += num_winners_at_this_rank
            continue

        total_prize_for_group = sum(prizes_to_share)
        prize_per_winner = total_prize_for_group / num_winners_at_this_rank

        for user in winners:
            user.balance += prize_per_winner
            history_entry = BalanceHistory(
                user_id=user.id,
                change_amount=prize_per_winner,
                new_balance=user.balance,
                description=f'Prize for sharing {current_rank}-{current_rank + num_winners_at_this_rank - 1} place in tournament: {tournament.name}'
            )
            db.session.add(history_entry)
            current_app.logger.info(f"Awarded {prize_per_winner:.2f} to {user.username} for sharing rank {current_rank} in tournament {tournament.id}")

        current_rank += num_winners_at_this_rank

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to commit prize distribution for tournament {tournament.id}: {e}")
        db.session.rollback()

@tournament_bp.route('/<int:tournament_id>/details')
@login_required
def details(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    user_is_participant = current_user in tournament.attendees
    form = PredictionForm()
    matches_data = json.loads(tournament.matches_json) if tournament.matches_json else []

    first_match_start_time = None
    if matches_data:
        sorted_matches = sorted(matches_data, key=lambda x: dateutil.parser.isoparse(x['fixture']['date']))
        if sorted_matches:
            first_match_date_str = sorted_matches[0]['fixture']['date']
            first_match_start_time = dateutil.parser.isoparse(first_match_date_str)

    now_utc = datetime.now(timezone.utc)
    user_predictions = {p.match_id: p for p in current_user.predictions.filter_by(tournament_id=tournament.id).all()}
    leaderboard = db.session.query(
        User.username,
        func.sum(Prediction.points_awarded).label('total_points')
    ).join(Prediction).filter(
        Prediction.tournament_id == tournament_id
    ).group_by(User.username).order_by(
        func.sum(Prediction.points_awarded).desc()
    ).all()

    return render_template(
        'tournament/details.html',
        tournament=tournament,
        matches=matches_data,
        user_is_participant=user_is_participant,
        form=form,
        user_predictions=user_predictions,
        leaderboard=leaderboard,
        first_match_start_time=first_match_start_time,
        now_utc=now_utc
    )

# ===== НАЧАЛО ИЗМЕНЕНИЙ: ЛОГИКА ФИЛЬТРАЦИИ =====
@tournament_bp.route('/')
def list_tournaments():
    query = Tournament.query.filter(Tournament.status != 'draft')

    # Получаем параметры фильтра из запроса
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    selected_sports = request.args.getlist('sport') # getlist для нескольких значений
    prize_places_str = request.args.get('prize_places')

    # Применяем фильтры к запросу
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(Tournament.start_date >= start_date)
        except ValueError:
            flash('Invalid start date format. Please use YYYY-MM-DD.', 'danger')
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            query = query.filter(Tournament.end_date <= end_date)
        except ValueError:
            flash('Invalid end date format. Please use YYYY-MM-DD.', 'danger')

    if selected_sports:
        query = query.filter(Tournament.sport.in_(selected_sports))

    if prize_places_str:
        try:
            prize_places = int(prize_places_str)
            if prize_places > 0:
                query = query.filter(Tournament.prize_places == prize_places)
        except ValueError:
            flash('Prize places must be a number.', 'danger')

    # Сортировка
    status_order = case(
        (Tournament.status == 'open', 1),
        (Tournament.status == 'active', 2),
        (Tournament.status == 'finished', 3),
        else_=4
    ).label("status_order")
    
    tournaments = query.order_by(status_order, Tournament.start_date.desc()).all()

    # Получаем все уникальные виды спорта из БД для формы фильтра
    available_sports = [s[0] for s in db.session.query(Tournament.sport).distinct().all()]

    return render_template(
        'tournament/list.html', 
        tournaments=tournaments, 
        title='Tournaments',
        available_sports=available_sports,
        filter_values=request.args # Передаем текущие значения фильтра обратно в шаблон
    )
# ===== КОНЕЦ ИЗМЕНЕНИЙ =====

@tournament_bp.route('/<int:tournament_id>')
def tournament_details(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    if tournament.status == 'open' and tournament.start_date and tournament.start_date <= datetime.utcnow():
        tournament.status = 'active'
        db.session.commit()
        flash('This tournament has now started!', 'info')

    league_names_by_id = {v: k for k, v in LEAGUES.items()}
    grouped_matches = defaultdict(lambda: defaultdict(list))
    matches_list = []
    if tournament.matches_json:
        try:
            matches_list = json.loads(tournament.matches_json)
            matches_list.sort(key=lambda x: x['fixture']['date'])
            for match in matches_list:
                league_id = match.get('league', {}).get('id', 0)
                league_name = league_names_by_id.get(league_id, 'Unknown League')
                round_name = match.get('league', {}).get('round', 'Regular Season')
                grouped_matches[league_name][round_name].append(match)
        except (json.JSONDecodeError, TypeError):
            flash('Could not parse match data for this tournament.', 'warning')

    can_leave = tournament.status in ['open', 'upcoming']
    if can_leave and matches_list:
        try:
            first_match_start_time = dateutil.parser.isoparse(matches_list[0]['fixture']['date'])
            if datetime.now(timezone.utc) >= first_match_start_time:
                can_leave = False
        except (ValueError, KeyError):
            can_leave = False

    num_attendees = len(tournament.attendees)
    form = PredictionForm()
    user_predictions = {}
    if current_user.is_authenticated:
        predictions = Prediction.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).all()
        for p in predictions:
            user_predictions[str(p.match_id)] = p

    leaderboard = db.session.query(User.username, func.sum(Prediction.points_awarded).label('total_points')).select_from(Prediction).join(User, Prediction.user_id == User.id).filter(Prediction.tournament_id == tournament.id).group_by(User.username).order_by(db.desc('total_points')).all()
    prize_distribution = calculate_prize_distribution(tournament, num_attendees)
    platform_fee = (num_attendees * tournament.entry_fee) * 0.10

    return render_template(
        'tournament/details.html',
        tournament=tournament,
        title=tournament.name,
        form=form,
        grouped_matches=grouped_matches,
        user_predictions=user_predictions,
        leaderboard=leaderboard,
        num_attendees=num_attendees,
        platform_fee=platform_fee,
        prize_distribution=prize_distribution,
        can_leave=can_leave,
        standings_urls=LEAGUE_STANDINGS_URLS
    )

@tournament_bp.route('/<int:tournament_id>/predict', methods=['POST'])
@login_required
def make_prediction(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    if tournament not in current_user.tournaments:
        flash('You must join the tournament before making predictions.', 'danger')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

    match_id_str = request.form.get('match_id')
    home_score_str = request.form.get(f'home_score_{match_id_str}')
    away_score_str = request.form.get(f'away_score_{match_id_str}')

    if not match_id_str or home_score_str is None or away_score_str is None:
        flash('Invalid prediction data submitted.', 'danger')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

    try:
        home_score = int(home_score_str)
        away_score = int(away_score_str)
    except (ValueError, TypeError):
        flash('Scores must be integer numbers.', 'danger')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

    prediction = Prediction.query.filter_by(user_id=current_user.id, tournament_id=tournament.id, match_id=match_id_str).first()

    if not tournament.matches_json:
        flash('Tournament has no match data.', 'danger')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

    all_matches_info = json.loads(tournament.matches_json)
    match_info = next((m for m in all_matches_info if str(m['fixture']['id']) == match_id_str), None)

    if not match_info:
        flash('Could not find match info to create or update prediction.', 'danger')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))

    if prediction:
        prediction.home_score_prediction = home_score
        prediction.away_score_prediction = away_score
        flash('Your prediction has been updated!', 'success')
    else:
        new_prediction = Prediction(user_id=current_user.id, tournament_id=tournament.id, match_id=match_id_str, match_date=dateutil.parser.isoparse(match_info['fixture']['date']), home_team=match_info['teams']['home']['name'], away_team=match_info['teams']['away']['name'], home_score_prediction=home_score, away_score_prediction=away_score, points_awarded=0)
        db.session.add(new_prediction)
        flash('Your prediction has been saved!', 'success')

    db.session.commit()
    return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id, _anchor=f'match-{match_id_str}'))

@tournament_bp.route('/<int:tournament_id>/action', methods=['POST'])
@login_required
def join_or_leave_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    action = request.form.get('action')

    if action == 'join':
        if tournament.max_participants and len(tournament.attendees) >= tournament.max_participants:
            flash('The tournament is full.', 'danger')
        elif current_user.balance < tournament.entry_fee:
            flash('You do not have enough funds to join this tournament.', 'danger')
        elif tournament in current_user.tournaments:
            flash('You are already in this tournament.', 'info')
        else:
            current_user.balance -= tournament.entry_fee
            history_entry = BalanceHistory(user_id=current_user.id, change_amount=-tournament.entry_fee, new_balance=current_user.balance, description=f'Entry fee for {tournament.name}')
            db.session.add(history_entry)
            tournament.attendees.append(current_user)
            db.session.commit()
            flash(f'You have successfully joined the tournament: {tournament.name}!', 'success')

    elif action == 'leave':
        first_match_start_time = None
        if tournament.matches_json:
            try:
                matches_list = json.loads(tournament.matches_json)
                if matches_list:
                    matches_list.sort(key=lambda x: x['fixture']['date'])
                    first_match_start_time = dateutil.parser.isoparse(matches_list[0]['fixture']['date'])
            except (json.JSONDecodeError, TypeError, IndexError):
                pass 

        can_leave = True
        if tournament.status not in ['open', 'upcoming']:
            can_leave = False
        if first_match_start_time and datetime.now(timezone.utc) >= first_match_start_time:
            can_leave = False

        if not can_leave:
            flash('You cannot leave a tournament that has already started.', 'danger')
        elif tournament not in current_user.tournaments:
            flash('You are not in this tournament.', 'info')
        else:
            current_user.balance += tournament.entry_fee
            history_entry = BalanceHistory(user_id=current_user.id, change_amount=tournament.entry_fee, new_balance=current_user.balance, description=f'Refund for leaving {tournament.name}')
            db.session.add(history_entry)
            tournament.attendees.remove(current_user)
            Prediction.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).delete()
            db.session.commit()
            flash(f'You have left the tournament: {tournament.name}.', 'success')

    return redirect(request.referrer or url_for('tournaments.list_tournaments'))

@tournament_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_or_organizer_required
def create_tournament():
    form = TournamentCreationForm()
    if form.validate_on_submit():
        new_tournament = Tournament(name=form.name.data, description=form.description.data, entry_fee=form.entry_fee.data, max_participants=form.max_participants.data, prize_places=form.prize_places.data, status='draft')
        db.session.add(new_tournament)
        db.session.commit()
        return redirect(url_for('tournaments.select_matches', tournament_id=new_tournament.id))
    return render_template('tournament/create_step1.html', title='Create Tournament - Step 1', form=form)

@tournament_bp.route('/<int:tournament_id>/select_matches', methods=['GET', 'POST'])
@login_required
@admin_or_organizer_required
def select_matches(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    available_sports = {'football': 'Football'} 

    if request.method == 'POST':
        matches_data_json = request.form.get('selected_matches_json')
        if not matches_data_json or matches_data_json == '[]':
            flash('Please select at least one match.', 'warning')
            return redirect(url_for('tournaments.select_matches', tournament_id=tournament.id))
        
        selected_sport = request.form.get('sport', 'football')
        tournament.sport = selected_sport

        tournament.matches_json = matches_data_json
        try:
            matches_data = json.loads(matches_data_json)
            if matches_data:
                match_dates = [dateutil.parser.isoparse(item['fixture']['date']) for item in matches_data]
                tournament.start_date = min(match_dates)
                tournament.end_date = max(match_dates)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            flash(f'Could not determine tournament dates from match data: {e}', 'warning')
        tournament.status = 'open'
        db.session.commit()
        flash('Tournament has been successfully created with selected matches!', 'success')
        return redirect(url_for('tournaments.tournament_details', tournament_id=tournament.id))
    
    return render_template('tournament/create_step2.html', title='Select Matches', tournament=tournament, leagues=LEAGUES, sports=available_sports)

@tournament_bp.route('/get_matches/<int:league_id>')
@login_required
@admin_or_organizer_required
def get_matches_by_league_id(league_id):
    matches = get_matches_for_league(league_id)
    if matches is None:
        return jsonify({'error': 'Failed to retrieve matches from API'}), 500
    return jsonify(matches)

@tournament_bp.route('/admin/tournament/<int:tournament_id>/manage', methods=['GET', 'POST'])
@login_required
@admin_or_organizer_required
def manage_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    matches = json.loads(tournament.matches_json) if tournament.matches_json else []
    existing_predictions = Prediction.query.filter(Prediction.tournament_id == tournament.id, Prediction.home_score_actual.isnot(None)).all()
    existing_results = {str(p.match_id): p for p in existing_predictions}

    if request.method == 'POST':
        form_name = request.form.get('form_name')

        if form_name == 'status_form':
            new_status = request.form.get('status')
            if new_status and new_status != tournament.status:
                if new_status == 'finished' and tournament.status != 'finished':
                    distribute_prizes_for_tournament(tournament)
                    flash('Prizes have been distributed!', 'success')
                tournament.status = new_status
                flash(f'Tournament status updated to {new_status}.', 'info')

        elif form_name == 'scores_form':
            updated_matches_count = 0
            for match in matches:
                match_id_str = str(match['fixture']['id'])
                home_score_str = request.form.get(f'home_score_{match_id_str}')
                away_score_str = request.form.get(f'away_score_{match_id_str}')
                if home_score_str and away_score_str:
                    try:
                        actual_home = int(home_score_str)
                        actual_away = int(away_score_str)
                        predictions_for_match = Prediction.query.filter_by(tournament_id=tournament.id, match_id=match_id_str).all()
                        for prediction in predictions_for_match:
                            prediction.home_score_actual = actual_home
                            prediction.away_score_actual = actual_away
                            prediction.points_awarded = calculate_points(prediction, actual_home, actual_away)
                        updated_matches_count += 1
                    except (ValueError, TypeError):
                        flash(f'Invalid score for match {match_id_str}. Must be numbers.', 'danger')
                        continue
            if updated_matches_count > 0:
                flash(f'Successfully updated scores and calculated points for {updated_matches_count} matches.', 'success')
            else:
                flash('No new scores were entered.', 'warning')

        db.session.commit()
        return redirect(url_for('tournaments.manage_tournament', tournament_id=tournament.id))

    return render_template('admin/manage_tournament.html', tournament=tournament, matches=matches, existing_results=existing_results)

@tournament_bp.route('/admin/tournament/<int:tournament_id>/redistribute', methods=['POST'])
@login_required
@admin_or_organizer_required
def redistribute_prizes(tournament_id):
    """
    Отменяет предыдущее распределение призов и запускает новое.
    """
    tournament = Tournament.query.get_or_404(tournament_id)
    if tournament.status != 'finished':
        flash('Prizes can only be redistributed for finished tournaments.', 'warning')
        return redirect(url_for('tournaments.manage_tournament', tournament_id=tournament_id))

    prize_history_entries = BalanceHistory.query.filter(
        BalanceHistory.description.like(f'%Prize%in tournament: {tournament.name}%'),
        BalanceHistory.user_id.in_([user.id for user in tournament.attendees])
    ).all()

    if not prize_history_entries:
        flash('No previous prize transactions found to reverse.', 'info')
    else:
        for entry in prize_history_entries:
            user = User.query.get(entry.user_id)
            if user:
                user.balance -= entry.change_amount
                current_app.logger.info(f"Reversing prize: -{entry.change_amount} from user {user.username}'s balance.")
            db.session.delete(entry)

        flash(f'Reversed {len(prize_history_entries)} previous prize transactions.', 'success')

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reversing prizes for tournament {tournament.id}: {e}")
        flash(f'Error reversing prizes: {e}', 'danger')
        return redirect(url_for('tournaments.manage_tournament', tournament_id=tournament_id))

    current_app.logger.info(f"Starting new prize distribution for tournament {tournament.id}.")
    distribute_prizes_for_tournament(tournament)

    flash('Prizes have been successfully redistributed!', 'success')
    return redirect(url_for('tournaments.manage_tournament', tournament_id=tournament_id))