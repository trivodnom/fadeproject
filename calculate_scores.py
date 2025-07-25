import os
import requests
from app import create_app, db
from app.models import Tournament, Prediction
from datetime import datetime

app = create_app()
app.app_context().push()

API_HOST = app.config['API_HOST']
API_KEY = app.config['API_KEY']

def get_finished_match_results(match_ids):
    """Получает результаты для списка ID матчей."""
    if not match_ids:
        return {}
    
    url = f"https://{API_HOST}/v3/fixtures"
    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': API_KEY}
    
    results = {}
    # API может принимать только ограниченное кол-во ID за раз, дробим на части
    for i in range(0, len(match_ids), 20):
        chunk = match_ids[i:i + 20]
        ids_string = "-".join(map(str, chunk))
        params = {'ids': ids_string}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json().get('response', [])
            
            for match in data:
                # Нас интересуют только завершенные матчи с результатом
                if match['fixture']['status']['short'] == 'FT' and match['goals']['home'] is not None:
                    results[match['fixture']['id']] = {
                        'home': match['goals']['home'],
                        'away': match['goals']['away']
                    }
        except Exception as e:
            print(f"API Error fetching results for IDs {ids_string}: {e}")
            
    return results

def calculate_points(prediction, actual):
    """Рассчитывает очки на основе прогноза и реального счета."""
    pred_home = prediction.home_score_prediction
    pred_away = prediction.away_score_prediction
    actual_home = actual['home']
    actual_away = actual['away']

    # 5 очков - точный счет
    if pred_home == actual_home and pred_away == actual_away:
        return 5

    # Определяем исход матча (победа хозяев, ничья, победа гостей)
    pred_outcome = 'draw' if pred_home == pred_away else ('home' if pred_home > pred_away else 'away')
    actual_outcome = 'draw' if actual_home == actual_away else ('home' if actual_home > actual_away else 'away')

    if pred_outcome == actual_outcome:
        # 3 очка - исход и разница мячей
        if abs(pred_home - pred_away) == abs(actual_home - actual_away):
            return 3
        # 2 очка - только исход
        return 2
    
    # 1 очко - угадано число голов одной из команд
    if pred_home == actual_home or pred_away == actual_away:
        return 1

    return 0

def run_calculation():
    print(f"[{datetime.utcnow()}] Starting score calculation...")
    # Ищем турниры, которые идут сейчас
    active_tournaments = Tournament.query.filter(
        Tournament.status == 'active',
        Tournament.start_date < datetime.utcnow()
    ).all()
    
    for tournament in active_tournaments:
        print(f"Processing tournament: {tournament.name}")
        
        # Собираем ID всех прогнозов, где очки еще не начислены
        pending_predictions = Prediction.query.filter(
            Prediction.tournament_id == tournament.id,
            Prediction.points_awarded == 0,
            Prediction.match_date < datetime.utcnow()
        ).all()
        
        if not pending_predictions:
            continue

        match_ids_to_check = list(set(p.match_id for p in pending_predictions))
        results = get_finished_match_results(match_ids_to_check)
        
        if not results:
            continue

        for prediction in pending_predictions:
            if prediction.match_id in results:
                actual_score = results[prediction.match_id]
                points = calculate_points(prediction, actual_score)
                prediction.points_awarded = points
                print(f"  Awarded {points} to user {prediction.user_id} for match {prediction.match_id}")

    db.session.commit()
    print(f"[{datetime.utcnow()}] Score calculation finished.")

if __name__ == '__main__':
    run_calculation()