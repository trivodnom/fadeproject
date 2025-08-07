import os
from flask import url_for, current_app
import dateutil.parser
from datetime import timezone, timedelta

# ----- НАЧАЛО НОВОГО КОДА -----
def versioned_url_for(endpoint, **values):
    """
    Создает URL для статического файла с добавлением времени его модификации.
    Это заставляет браузеры перезагружать измененные CSS и JS файлы.
    """
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            # Строим полный путь к файлу
            file_path = os.path.join(current_app.static_folder, filename)
            if os.path.exists(file_path):
                # Добавляем временную метку как параметр 'v'
                values['v'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)
# ----- КОНЕЦ НОВОГО КОДА -----


def format_datetime_filter(value):
    """Форматирует строку даты ISO в читаемый формат по МСК (UTC+3)."""
    if not value:
        return ""
    try:
        # 1. Парсим строку в объект datetime с информацией о таймзоне (он уже в UTC)
        dt_object_utc = dateutil.parser.isoparse(value)
        
        # 2. Создаем объект таймзоны для МСК (UTC+3)
        msk_tz = timezone(timedelta(hours=3))
        
        # 3. Конвертируем время в таймзону МСК
        dt_object_msk = dt_object_utc.astimezone(msk_tz)
        
        # 4. Форматируем
        return dt_object_msk.strftime('%d %b %Y, %H:%M')
    except (ValueError, TypeError):
        return value