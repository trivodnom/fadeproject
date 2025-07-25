import requests
from flask import current_app
from datetime import datetime, timedelta

LEAGUES = {
    'Premier League': 39, 
    'La Liga': 140, 
    'Bundesliga': 78, 
    'Serie A': 135, 
    'Ligue 1': 61, 
    'Russian Premier League': 235, 
    'Kazakhstan Premier League': 389
}

def get_matches_for_league(league_id, days=30):
    """Получает предстоящие матчи для указанной лиги."""
    api_host = current_app.config['API_HOST']
    api_key = current_app.config['API_KEY']
    
    params = {
        'league': league_id,
        'season': datetime.utcnow().year,
        'from': datetime.utcnow().strftime('%Y-%m-%d'),
        'to': (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d'),
        'status': 'NS'
    }
    
    # ИСПРАВЛЕНИЕ: Добавили /v3/
    url = f"https://{api_host}/v3/fixtures"
    headers = {'x-rapidapi-host': api_host, 'x-rapidapi-key': api_key}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('response', [])
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None