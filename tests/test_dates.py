from datetime import date, datetime, timezone

from core.dates import (
    bank_holidays,
    berlin_date,
    berlin_offset_hours,
    easter_sunday,
    is_business_day,
    is_month_end,
    is_quarter_end,
    month_end,
    month_start,
    next_business_day,
    parse_date,
    quarter_start,
    utc_now,
)


def test_berlin_offset():
    assert berlin_offset_hours(datetime(2025, 1, 15, 7, tzinfo=timezone.utc)) == 1
    assert berlin_offset_hours(datetime(2025, 7, 15, 15, tzinfo=timezone.utc)) == 2


def test_berlin_date():
    assert berlin_date(datetime(2025, 6, 2, 8, 45, tzinfo=timezone.utc)) == date(2025, 6, 2)


def test_easter():
    assert easter_sunday(2025) == date(2025, 4, 20)


def test_holidays_contain_new_year_and_good_friday():
    holidays = bank_holidays(2025)
    assert date(2025, 1, 1) in holidays
    assert date(2025, 4, 18) in holidays


def test_business_days():
    assert is_business_day(date(2025, 3, 3))
    assert not is_business_day(date(2025, 3, 2))
    assert not is_business_day(date(2025, 12, 25))
    assert next_business_day(date(2025, 3, 1)) == date(2025, 3, 3)
    assert next_business_day(date(2025, 3, 3)) == date(2025, 3, 3)


def test_period_helpers():
    assert month_start(date(2025, 2, 14)) == date(2025, 2, 1)
    assert month_end(date(2025, 2, 14)) == date(2025, 2, 28)
    assert month_end(date(2025, 12, 1)) == date(2025, 12, 31)
    assert quarter_start(date(2025, 5, 20)) == date(2025, 4, 1)
    assert is_month_end(date(2025, 4, 30))
    assert not is_month_end(date(2025, 4, 29))
    assert is_quarter_end(date(2025, 6, 30))
    assert not is_quarter_end(date(2025, 5, 31))


def test_parse_date():
    assert parse_date("2025-03-01") == date(2025, 3, 1)
    assert parse_date(date(2025, 3, 1)) == date(2025, 3, 1)


def test_utc_now_is_aware():
    assert utc_now().tzinfo is not None
