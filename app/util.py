import dateutil.parser

def format_datetime_filter(value):
    """Форматирует строку даты ISO в читаемый формат."""
    if not value:
        return ""
    try:
        dt_object = dateutil.parser.isoparse(value)
        return dt_object.strftime('%d %b %Y, %H:%M')
    except (ValueError, TypeError):
        return value