"""Calendar helpers: Europe/Berlin local time, business days, period boundaries."""
from datetime import date, datetime, timedelta, timezone


def utc_now():
    return datetime.now(timezone.utc)


def _last_sunday(year, month):
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def berlin_offset_hours(moment):
    """UTC offset of Europe/Berlin at an aware datetime.

    Summer time runs from 01:00 UTC on the last Sunday of March to 01:00 UTC on
    the last Sunday of October. Kept local because the batch hosts do not all
    carry a time zone database.
    """
    utc = moment.astimezone(timezone.utc)
    start = datetime.combine(_last_sunday(utc.year, 3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    end = datetime.combine(_last_sunday(utc.year, 10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    return 2 if start <= utc < end else 1


def berlin_time(moment):
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone(timedelta(hours=berlin_offset_hours(moment))))


def berlin_date(moment):
    return berlin_time(moment).date()


def easter_sunday(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def bank_holidays(year):
    """Bank holidays observed by Musterbank AG."""
    easter = easter_sunday(year)
    return {
        date(year, 1, 1),
        easter - timedelta(days=2),
        easter + timedelta(days=1),
        date(year, 5, 1),
        easter + timedelta(days=39),
        easter + timedelta(days=50),
        date(year, 10, 3),
        date(year, 12, 24),
        date(year, 12, 25),
        date(year, 12, 26),
        date(year, 12, 31),
    }


def is_business_day(day):
    if day.weekday() >= 5:
        return False
    return day not in bank_holidays(day.year)


def next_business_day(day):
    """The given day if it is a business day, otherwise the next one."""
    while not is_business_day(day):
        day = day + timedelta(days=1)
    return day


def month_start(day):
    return day.replace(day=1)


def month_end(day):
    if day.month == 12:
        return date(day.year, 12, 31)
    return date(day.year, day.month + 1, 1) - timedelta(days=1)


def quarter_start(day):
    return date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)


def is_month_end(day):
    return day == month_end(day)


def is_quarter_end(day):
    return is_month_end(day) and day.month % 3 == 0


def parse_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)
