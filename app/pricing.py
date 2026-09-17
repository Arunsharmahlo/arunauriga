import math
from datetime import datetime


# These values are configurable.
# Replace them with the exact values provided by Auriga
# if the assessment specifies different rates.

FIRST_HOUR_RATE = 50.0
ADDITIONAL_HOUR_RATE = 30.0
DAILY_CAP = 300.0


def calculate_billable_hours(entry_time: datetime, exit_time: datetime) -> int:
    duration_seconds = (exit_time - entry_time).total_seconds()

    if duration_seconds <= 0:
        return 0

    duration_hours = duration_seconds / 3600
    return math.ceil(duration_hours)


def calculate_fee(
    entry_time: datetime,
    exit_time: datetime,
) -> float:

    hours = calculate_billable_hours(entry_time, exit_time)

    if hours == 0:
        return 0.0

    if hours == 1:
        fee = FIRST_HOUR_RATE
    else:
        fee = FIRST_HOUR_RATE + (
            (hours - 1) * ADDITIONAL_HOUR_RATE
        )

    return min(fee, DAILY_CAP)