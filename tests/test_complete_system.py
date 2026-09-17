from datetime import datetime, timedelta

import pytest

from app.database import Base, SessionLocal, engine
from app.models import ParkingSpot, ParkingSession
from app.parking import ParkingManager
from app.pricing import (
    calculate_billable_hours,
    calculate_fee,
    clean_rate_card,
)


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


def create_garage(db):
    manager = ParkingManager(db)

    manager.add_spot(
        1,
        "C-101",
        "COMPACT"
    )

    manager.add_spot(
        1,
        "S-101",
        "STANDARD"
    )

    manager.add_spot(
        1,
        "E-101",
        "EV"
    )

    return manager


# =========================
# PRICING
# =========================

def test_first_hour():
    entry = datetime(2026, 9, 17, 10, 0)
    exit = datetime(2026, 9, 17, 11, 0)

    assert calculate_fee(
        entry,
        exit
    ) == 50.0


def test_additional_hour():
    entry = datetime(2026, 9, 17, 10, 0)
    exit = datetime(2026, 9, 17, 12, 0)

    assert calculate_fee(
        entry,
        exit
    ) == 80.0


def test_partial_hour_rounds_up():
    entry = datetime(2026, 9, 17, 10, 0)
    exit = datetime(2026, 9, 17, 11, 1)

    assert calculate_billable_hours(
        entry,
        exit
    ) == 2


def test_daily_cap():
    entry = datetime(2026, 9, 17, 10, 0)
    exit = entry + timedelta(hours=20)

    assert calculate_fee(
        entry,
        exit
    ) == 300.0


# =========================
# T4 RATE CARD
# =========================

def test_messy_rate_card_is_cleaned():
    messy = {
        " compact ": {
            "first_hour": "₹60",
            "additional_hour": " Rs. 25 ",
            "daily_cap": "₹250"
        },
        "STANDARD": {
            "first_hour": "₹70.00",
            "additional_hour": "30",
            "daily_cap": "₹300"
        },
        "ev": {
            "first_hour": "₹80",
            "additional_hour": "₹40",
            "daily_cap": "₹350"
        }
    }

    cleaned = clean_rate_card(messy)

    assert cleaned["COMPACT"]["first_hour"] == 60.0
    assert cleaned["COMPACT"]["additional_hour"] == 25.0
    assert cleaned["COMPACT"]["daily_cap"] == 250.0

    assert cleaned["STANDARD"]["first_hour"] == 70.0
    assert cleaned["EV"]["first_hour"] == 80.0


def test_imported_rates_are_used(db):
    manager = create_garage(db)

    manager.import_rate_card({
        "EV": {
            "first_hour": "₹80",
            "additional_hour": "₹40",
            "daily_cap": "₹350"
        }
    })

    entry = datetime(2026, 9, 17, 10, 0)
    exit = datetime(2026, 9, 17, 12, 0)

    manager.check_in(
        "EV001",
        "EV",
        entry
    )

    session = manager.check_out(
        "EV001",
        exit
    )

    assert session.fee == 120.0


# =========================
# PARKING TYPES
# =========================

def test_compact_vehicle(db):
    manager = create_garage(db)

    session = manager.check_in(
        "CAR001",
        "COMPACT",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = (
        db.query(ParkingSpot)
        .filter(
            ParkingSpot.id == session.spot_id
        )
        .first()
    )

    assert spot.spot_type == "COMPACT"


def test_standard_vehicle(db):
    manager = create_garage(db)

    session = manager.check_in(
        "CAR002",
        "STANDARD",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = (
        db.query(ParkingSpot)
        .filter(
            ParkingSpot.id == session.spot_id
        )
        .first()
    )

    assert spot.spot_type == "STANDARD"


def test_ev_gets_ev_spot(db):
    manager = create_garage(db)

    session = manager.check_in(
        "EV001",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = (
        db.query(ParkingSpot)
        .filter(
            ParkingSpot.id == session.spot_id
        )
        .first()
    )

    assert spot.spot_type == "EV"


def test_ev_cannot_use_standard(db):
    manager = ParkingManager(db)

    manager.add_spot(
        1,
        "S-101",
        "STANDARD"
    )

    with pytest.raises(ValueError):
        manager.check_in(
            "EV001",
            "EV",
            datetime(2026, 9, 17, 10, 0)
        )


# =========================
# DUPLICATE PARKING
# =========================

def test_duplicate_vehicle_rejected(db):
    manager = create_garage(db)

    manager.check_in(
        "CAR001",
        "COMPACT",
        datetime(2026, 9, 17, 10, 0)
    )

    with pytest.raises(ValueError):
        manager.check_in(
            "CAR001",
            "COMPACT",
            datetime(2026, 9, 17, 11, 0)
        )


# =========================
# LOOKUP
# =========================

def test_plate_lookup(db):
    manager = create_garage(db)

    manager.check_in(
        "CAR001",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = manager.get_vehicle_location(
        "CAR001"
    )

    assert spot is not None
    assert spot.spot_number == "E-101"


# =========================
# CHECKOUT
# =========================

def test_checkout_releases_spot(db):
    manager = create_garage(db)

    manager.check_in(
        "CAR001",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    manager.check_out(
        "CAR001",
        datetime(2026, 9, 17, 12, 0)
    )

    spot = (
        db.query(ParkingSpot)
        .filter(
            ParkingSpot.spot_number == "E-101"
        )
        .first()
    )

    assert spot.is_occupied is False


# =========================
# EV AVAILABILITY
# =========================

def test_ev_availability(db):
    manager = create_garage(db)

    assert (
        manager.is_ev_spot_available()
        is True
    )

    manager.check_in(
        "EV001",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    assert (
        manager.is_ev_spot_available()
        is False
    )


# =========================
# T2 CLOCK
# =========================

def test_clock_auto_closes_over_24_hours(db):
    manager = create_garage(db)

    entry = datetime(
        2026, 9, 17, 10, 0
    )

    current_time = datetime(
        2026, 9, 18, 11, 0
    )

    manager.check_in(
        "CAR001",
        "EV",
        entry
    )

    closed = manager.process_clock(
        current_time
    )

    assert len(closed) == 1

    session = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.plate_number
            == "CAR001"
        )
        .first()
    )

    assert session.is_active is False
    assert session.exit_time == current_time
    assert session.fee == 300.0


def test_clock_does_not_close_under_24_hours(db):
    manager = create_garage(db)

    entry = datetime(
        2026, 9, 17, 10, 0
    )

    current_time = datetime(
        2026, 9, 18, 9, 59
    )

    manager.check_in(
        "CAR001",
        "EV",
        entry
    )

    closed = manager.process_clock(
        current_time
    )

    assert len(closed) == 0


# =========================
# T6 TRANSFER
# =========================

def test_transfer_keeps_spot_and_entry_time(db):
    manager = create_garage(db)

    entry = datetime(
        2026, 9, 17, 10, 0
    )

    session = manager.check_in(
        "OLD001",
        "EV",
        entry
    )

    original_spot_id = session.spot_id

    transferred = manager.transfer_session(
        "OLD001",
        "NEW001"
    )

    assert transferred.plate_number == "NEW001"

    assert (
        transferred.spot_id
        == original_spot_id
    )

    assert (
        transferred.entry_time
        == entry
    )

    assert (
        manager.find_active_vehicle(
            "OLD001"
        )
        is None
    )

    assert (
        manager.find_active_vehicle(
            "NEW001"
        )
        is not None
    )


def test_transfer_to_existing_plate_rejected(db):
    manager = create_garage(db)

    manager.check_in(
        "OLD001",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    manager.check_in(
        "NEW001",
        "COMPACT",
        datetime(2026, 9, 17, 10, 0)
    )

    with pytest.raises(ValueError):
        manager.transfer_session(
            "OLD001",
            "NEW001"
        )