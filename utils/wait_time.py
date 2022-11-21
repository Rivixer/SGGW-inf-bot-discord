from datetime import datetime, timedelta


def time_to_midnight() -> int:
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    midnight = datetime(
        year=tomorrow.year,
        month=tomorrow.month,
        day=tomorrow.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    time_to_midnight = midnight - today
    return time_to_midnight.seconds
