import math
from datetime import datetime


DEFAULT_RATES = {
    "COMPACT": {
        "first_hour": 50.0,
        "additional_hour": 30.0,
        "daily_cap": 300.0,
    },
    "STANDARD": {
        "first_hour": 50.0,
        "additional_hour": 30.0,
        "daily_cap": 300.0,
    },
    "EV": {
        "first_hour": 50.0,
        "additional_hour": 30.0,
        "daily_cap": 300.0,
    },
}


def calculate_billable_hours(
    entry_time: datetime,
    exit_time: datetime
) -> int:
    duration_seconds = (
        exit_time - entry_time
    ).total_seconds()

    if duration_seconds <= 0:
        return 0

    duration_hours = duration_seconds / 3600

    return math.ceil(duration_hours)


def calculate_fee(
    entry_time: datetime,
    exit_time: datetime,
    spot_type: str = "STANDARD",
    rates: dict | None = None
) -> float:

    spot_type = spot_type.upper()

    if rates is None:
        rates = DEFAULT_RATES

    if spot_type not in rates:
        raise ValueError(
            f"No rate configured for spot type: {spot_type}"
        )

    rate = rates[spot_type]

    hours = calculate_billable_hours(
        entry_time,
        exit_time
    )

    if hours == 0:
        return 0.0

    if hours == 1:
        fee = rate["first_hour"]
    else:
        fee = (
            rate["first_hour"]
            + (
                (hours - 1)
                * rate["additional_hour"]
            )
        )

    return min(
        fee,
        rate["daily_cap"]
    )