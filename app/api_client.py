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
    """Получает предстоящие матчи для указанной лиги с логированием."""
    api_host = current_app.config['API_HOST']
    api_key = current_app.config['API_KEY']

    # --- НАЧАЛО БЛОКА ЛОГИРОВАНИЯ ---
    print("--- API: Requesting UPCOMING matches ---")

    # Определяем текущий год для сезона
    current_year = datetime.utcnow().year

    params = {
        'league': league_id,
        'season': current_year, # Используем текущий год
        'status': 'NS' # Not Started
    }

    url = f"https://{api_host}/v3/fixtures"
    headers = {'x-rapidapi-host': api_host, 'x-rapidapi-key': api_key}

    print(f"URL: {url}")
    print(f"Headers: {{'x-rapidapi-host': '{api_host}', 'x-rapidapi-key': '***'}}") # Прячем ключ из логов
    print(f"Params: {params}")
    # --- КОНЕЦ БЛОКА ЛОГИРОВАНИЯ ---

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        print(f"API Response Status: {response.status_code}")
        # print(f"API Raw Response: {response.text}") # <-- Раскомментируйте, если нужно видеть полный ответ

        response.raise_for_status()
        data = response.json()

        print(f"API found {len(data.get('response', []))} matches.")
        return data.get('response', [])
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

def get_finished_match_results_by_date(date_string):
    """Получает результаты всех завершенных матчей за конкретную дату с логированием."""
    api_host = current_app.config['API_HOST']
    api_key = current_app.config['API_KEY']

    params = {'date': date_string, 'status': 'FT'}
    url = f"https://{api_host}/v3/fixtures"
    headers = {'x-rapidapi-host': api_host, 'x-rapidapi-key': api_key}

    print("--- API: Requesting FINISHED matches ---")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"API Response Status: {response.status_code}")
        print(f"API Raw Response: {response.text}")
        response.raise_for_status()
        data = response.json().get('response', [])

        results = {}
        for match in data:
            if match.get('goals', {}).get('home') is not None:
                results[match['fixture']['id']] = {
                    'home': match['goals']['home'],
                    'away': match['goals']['away']
                }
        return results
    except Exception as e:
        print(f"API Error fetching results for date {date_string}: {e}")
        return {}