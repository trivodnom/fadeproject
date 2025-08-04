import dateutil.parser
from datetime import timezone, timedelta

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