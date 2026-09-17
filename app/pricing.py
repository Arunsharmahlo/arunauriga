import math
import re
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


def clean_number(value) -> float:
    """
    Convert messy rate values into numbers.

    Examples:
        ₹50       -> 50.0
        ₹50.00    -> 50.0
        Rs. 50    -> 50.0
        Rs 50     -> 50.0
        $50       -> 50.0
        1,000     -> 1000.0
        " 50 "    -> 50.0
    """

    if value is None:
        raise ValueError(
            "Rate value cannot be empty"
        )

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    # Remove common currency prefixes first.
    text = re.sub(
        r"(?i)\brs\.?\s*",
        "",
        text
    )

    text = re.sub(
        r"(?i)\binr\.?\s*",
        "",
        text
    )

    # Remove currency symbols.
    text = re.sub(
        r"[₹$€£]",
        "",
        text
    )

    # Remove commas and whitespace.
    text = text.replace(",", "")
    text = text.strip()

    # Extract the first valid numeric value.
    match = re.search(
        r"\d+(?:\.\d+)?",
        text
    )

    if not match:
        raise ValueError(
            f"Invalid rate value: {value}"
        )

    return float(match.group())


def clean_rate_card(rate_card: dict) -> dict:
    """
    Clean a messy rate card.

    Expected structure:

    {
        "compact": {
            "first_hour": "₹50",
            "additional_hour": "Rs. 30",
            "daily_cap": "₹300"
        }
    }
    """

    cleaned_rates = {}

    if not isinstance(rate_card, dict):
        return cleaned_rates

    for spot_type, values in rate_card.items():

        normalized_type = (
            str(spot_type)
            .strip()
            .upper()
        )

        if normalized_type not in {
            "COMPACT",
            "STANDARD",
            "EV"
        }:
            continue

        if not isinstance(values, dict):
            continue

        first_hour = values.get(
            "first_hour"
        )

        additional_hour = values.get(
            "additional_hour"
        )

        daily_cap = values.get(
            "daily_cap"
        )

        if (
            first_hour is None
            or additional_hour is None
            or daily_cap is None
        ):
            continue

        try:
            cleaned_rates[
                normalized_type
            ] = {
                "first_hour":
                    clean_number(first_hour),

                "additional_hour":
                    clean_number(
                        additional_hour
                    ),

                "daily_cap":
                    clean_number(
                        daily_cap
                    ),
            }

        except ValueError:
            continue

    return cleaned_rates


def calculate_billable_hours(
    entry_time: datetime,
    exit_time: datetime
) -> int:

    duration_seconds = (
        exit_time - entry_time
    ).total_seconds()

    if duration_seconds <= 0:
        return 0

    duration_hours = (
        duration_seconds / 3600
    )

    return math.ceil(
        duration_hours
    )


def calculate_fee(
    entry_time: datetime,
    exit_time: datetime,
    spot_type: str = "STANDARD",
    rates: dict | None = None
) -> float:

    spot_type = spot_type.strip().upper()

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