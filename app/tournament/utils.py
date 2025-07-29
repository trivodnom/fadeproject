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