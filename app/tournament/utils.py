def calculate_points(prediction, actual_home, actual_away):
    """
    Начисляет очки за прогноз в соответствии с правилами.
    - 5 очков: угадан точный счет.
    - 3 очка: угадана разница мячей и исход.
    - 2 очка: угадан только исход.
    - 1 очко: угадано количество голов одной из команд.
    """
    # Проверяем, что все данные на месте
    if prediction.home_score_prediction is None or prediction.away_score_prediction is None:
        return 0

    pred_home = prediction.home_score_prediction
    pred_away = prediction.away_score_prediction

    # 5 очков: точный счет
    if pred_home == actual_home and pred_away == actual_away:
        return 5

    # Определяем исходы (победа хозяев, победа гостей, ничья)
    pred_outcome = 'draw' if pred_home == pred_away else ('home' if pred_home > pred_away else 'away')
    actual_outcome = 'draw' if actual_home == actual_away else ('home' if actual_home > actual_away else 'away')

    # 3 очка: угадан исход и разница мячей
    if pred_outcome == actual_outcome and (pred_home - pred_away) == (actual_home - actual_away):
        return 3

    # 2 очка: угадан только исход
    if pred_outcome == actual_outcome:
        return 2

    # 1 очко: угадано количество голов одной из команд
    if pred_home == actual_home or pred_away == actual_away:
        return 1

    return 0

def calculate_prize_distribution(tournament, num_attendees, return_raw=False):
    """Рассчитывает распределение призов по утвержденной логике."""
    entry_fee = tournament.entry_fee
    prize_places = tournament.prize_places

    if num_attendees == 0 or entry_fee == 0 or prize_places == 0:
        # Если возвращаем сырые данные, то пустой словарь, иначе - список
        return {} if return_raw else ["No prizes yet."]

    total_pool = entry_fee * num_attendees
    net_prize_pool = total_pool * 0.90

    prizes = {}

    if prize_places == 1:
        prizes[1] = net_prize_pool

    elif prize_places == 2:
        if num_attendees < 3:
            prizes[1] = net_prize_pool
        else:
            prizes[2] = entry_fee
            if net_prize_pool > entry_fee:
                prizes[1] = net_prize_pool - entry_fee
            else:
                prizes[1] = 0

    elif prize_places == 3:
        if num_attendees < 4:
            if num_attendees >= 3:
                prizes[2] = entry_fee
                if net_prize_pool > entry_fee:
                    prizes[1] = net_prize_pool - entry_fee
                else:
                    prizes[1] = 0
            else:
                prizes[1] = net_prize_pool
        elif num_attendees == 4:
            prizes[3] = entry_fee
            prizes[2] = entry_fee
            prizes[1] = net_prize_pool - (2 * entry_fee)
        else:
            prizes[3] = entry_fee
            remainder = net_prize_pool - entry_fee
            prizes[1] = remainder * 0.65
            prizes[2] = remainder * 0.35

    if return_raw:
        return prizes # Возвращаем словарь {1: 500, 2: 300}

    if not prizes:
        return [f"Distribution not defined for {num_attendees} participants and {prize_places} places."]

    prize_list = [f"{k}-е место: {v:.2f} ₽" for k, v in sorted(prizes.items())]
    return prize_list