import requests
from flask import current_app
from datetime import datetime
from collections import defaultdict
import re

LEAGUES = {
    'Premier League': 39,
    'La Liga': 140,
    'Bundesliga': 78,
    'Serie A': 135,
    'Ligue 1': 61,
    'Russian Premier League': 235,
    'Kazakhstan Premier League': 389
}

# ===== НАЧАЛО НОВОГО КОДА =====
LEAGUE_STANDINGS_URLS = {
    39: 'https://www.flashscorekz.com/football/england/premier-league/standings/#/OEEq9Yvp/table/overall',
    140: 'https://www.flashscorekz.com/football/spain/laliga/standings/#/vcm2MhGk/table/overall',
    78: 'https://www.flashscorekz.com/football/germany/bundesliga/standings/#/8UYeqfiD/table/overall',
    135: 'https://www.flashscorekz.com/football/italy/serie-a/standings/#/6PWwAsA7/table/overall',
    61: 'https://www.flashscorekz.com/football/france/ligue-1/standings/#/j9QeTLPP/table/overall',
    235: 'https://www.flashscorekz.com/football/russia/premier-league/standings/#/0UC6tdRa/table/overall',
    389: 'https://www.flashscorekz.com/football/kazakhstan/premier-league/standings/#/4CxUrL2I/table/overall'
}
# ===== КОНЕЦ НОВОГО КОДА =====

def get_matches_for_league(league_id):
    """Получает предстоящие матчи для лиги, сгруппированные и отсортированные по турам."""
    api_host = current_app.config['API_HOST']
    api_key = current_app.config['API_KEY']

    params = {
        'league': league_id,
        'season': datetime.utcnow().year,
        'status': 'NS'
    }

    url = f"https://{api_host}/v3/fixtures"
    headers = {'x-rapidapi-host': api_host, 'x-rapidapi-key': api_key}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json().get('response', [])

        if not data:
            return {}

        grouped_by_round = defaultdict(list)
        for match in data:
            round_name = match.get('league', {}).get('round', 'Regular Season')
            grouped_by_round[round_name].append(match)

        def sort_key(round_name):
            numbers = re.findall(r'\d+', round_name)
            return int(numbers[0]) if numbers else 0

        sorted_rounds = sorted(grouped_by_round.keys(), key=sort_key)

        # ИЗМЕНЕНИЕ: Вместо словаря возвращаем список пар [название_тура, [матчи]]
        # Этот формат гарантирует сохранение порядка в JSON и JavaScript
        result_list = [[round_name, grouped_by_round[round_name]] for round_name in sorted_rounds]

        return result_list

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

def get_finished_match_results_by_date(date_string):
    # Эта функция остается без изменений
    api_host = current_app.config['API_HOST']
    api_key = current_app.config['API_KEY']
    params = {'date': date_string, 'status': 'FT'}
    url = f"https://{api_host}/v3/fixtures"
    headers = {'x-rapidapi-host': api_host, 'x-rapidapi-key': api_key}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
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