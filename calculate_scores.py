import os
import requests
import json
from datetime import datetime, timedelta
from sqlalchemy import func
from app import create_app, db
from app.models import Tournament, Prediction

from app import create_app, db
app = create_app()
app.app_context().push()

from app.models import Tournament, Prediction, User, BalanceHistory
from app.api_client import get_finished_match_results_by_date

def calculate_points(prediction):
    if prediction.home_score_actual is None or prediction.away_score_actual is None or \
       prediction.home_score_prediction is None or prediction.away_score_prediction is None:
        return 0

    pred_home, pred_away = prediction.home_score_prediction, prediction.away_score_prediction
    actual_home, actual_away = prediction.home_score_actual, prediction.away_score_actual

    if pred_home == actual_home and pred_away == actual_away: return 5
    pred_outcome = 'd' if pred_home == pred_away else ('h' if pred_home > pred_away else 'a')
    actual_outcome = 'd' if actual_home == actual_away else ('h' if actual_home > actual_away else 'a')
    if pred_outcome == actual_outcome:
        return 3 if abs(pred_home - pred_away) == abs(actual_home - actual_away) else 2
    if pred_home == actual_home or pred_away == actual_away: return 1
    return 0

def run_calculation_for_tournaments(ids):
    app = create_app()
    with app.app_context():
        count = 0
        for tournament_id in ids:
            tournament = Tournament.query.get(tournament_id)
            if not tournament: continue

            print(f"Calculating for tournament: {tournament.name}")
            for prediction in tournament.predictions:
                points = calculate_points(prediction)
                prediction.points_awarded = points
            count += 1
        db.session.commit()
        return count

def calculate_points(prediction, actual):
    if prediction.home_score_prediction is None or prediction.away_score_prediction is None:
        return 0
    pred_home, pred_away = prediction.home_score_prediction, prediction.away_score_prediction
    actual_home, actual_away = actual['home'], actual['away']
    if pred_home == actual_home and pred_away == actual_away:
        return 5
    pred_outcome = 'd' if pred_home == pred_away else ('h' if pred_home > pred_away else 'a')
    actual_outcome = 'd' if actual_home == actual_away else ('h' if actual_home > actual_away else 'a')
    if pred_outcome == actual_outcome:
        return 3 if abs(pred_home - pred_away) == abs(actual_home - actual_away) else 2
    if pred_home == actual_home or pred_away == actual_away: return 1
    return 0

def distribute_prizes(tournament):
    print(f"Distributing prizes for {tournament.name}...")
    # TODO: Implement prize distribution logic

def run_calculation():
    print(f"[{datetime.now()}] Starting score calculation...")

    tournaments_to_process = Tournament.query.filter(
        Tournament.status.in_(['active', 'finished'])
    ).all()

    for tournament in tournaments_to_process:
        print(f"Processing tournament: {tournament.name}")
        results = {}

        if tournament.manual_results:
            try:
                results = json.loads(tournament.manual_results)
                print(f"  Found {len(results)} manual results.")
            except json.JSONDecodeError:
                print("  Could not parse manual results JSON.")

        if not results:
            dates_to_check = list(set(p.match_date.strftime('%Y-%m-%d') for p in tournament.predictions if p.points_awarded == 0))
            for date_str in dates_to_check:
                api_results = get_finished_match_results_by_date(date_str)
                results.update(api_results)

        pending_predictions = Prediction.query.filter(
            Prediction.tournament_id == tournament.id,
            Prediction.points_awarded == 0
        ).all()

        if not pending_predictions:
            print("  No pending predictions to update.")
            continue

        for prediction in pending_predictions:
            # Convert match_id to int for correct key comparison
            if prediction.match_id in [int(k) for k in results.keys()]:
                actual_score = results[str(prediction.match_id)] # Keys in JSON are always strings
                prediction.home_score_actual = actual_score['home']
                prediction.away_score_actual = actual_score['away']
                points = calculate_points(prediction, actual_score)
                prediction.points_awarded = points
                print(f"    Awarded {points} points to user {prediction.user_id} for match {prediction.match_id}")

    db.session.commit()
    print(f"[{datetime.now()}] Score calculation finished.")

if __name__ == '__main__':
    run_calculation()