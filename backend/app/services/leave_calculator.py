
from datetime import date, timedelta


def calculate_working_days(start_date: date, end_date: date) -> int:
    """Count Monday-Friday between two dates, inclusive."""
    if end_date < start_date:
        raise ValueError("End date cannot be before start date.")

    working_days = 0
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5:
            working_days += 1

        current_date += timedelta(days=1)

    return working_days


def calculate_working_days_by_year(
    start_date: date,
    end_date: date,
) -> dict[int, int]:
    """Count working days separately for each calendar year."""
    if end_date < start_date:
        raise ValueError("End date cannot be before start date.")

    days_by_year: dict[int, int] = {}
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5:
            year = current_date.year
            days_by_year[year] = days_by_year.get(year, 0) + 1

        current_date += timedelta(days=1)

    return days_by_year

