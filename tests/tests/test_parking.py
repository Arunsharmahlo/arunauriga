from datetime import datetime

import pytest

from app.database import Base, SessionLocal, engine
from app.models import ParkingSpot
from app.parking import ParkingManager


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


def create_basic_garage(db):
    manager = ParkingManager(db)

    manager.add_spot(1, "C-101", "COMPACT")
    manager.add_spot(1, "S-101", "STANDARD")
    manager.add_spot(1, "E-101", "EV")

    return manager


def test_compact_vehicle_gets_compact_spot(db):
    manager = create_basic_garage(db)

    session = manager.check_in(
        "RJ14AB1001",
        "COMPACT",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == session.spot_id)
        .first()
    )

    assert spot.spot_type == "COMPACT"


def test_standard_vehicle_gets_standard_spot(db):
    manager = create_basic_garage(db)

    session = manager.check_in(
        "RJ14AB1002",
        "STANDARD",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == session.spot_id)
        .first()
    )

    assert spot.spot_type == "STANDARD"


def test_ev_vehicle_gets_ev_spot(db):
    manager = create_basic_garage(db)

    session = manager.check_in(
        "RJ14AB1003",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == session.spot_id)
        .first()
    )

    assert spot.spot_type == "EV"
    assert spot.spot_number == "E-101"


def test_ev_cannot_use_standard_spot(db):
    manager = ParkingManager(db)

    manager.add_spot(1, "S-101", "STANDARD")

    with pytest.raises(ValueError):
        manager.check_in(
            "RJ14AB1004",
            "EV",
            datetime(2026, 9, 17, 10, 0)
        )


def test_duplicate_vehicle_is_rejected(db):
    manager = create_basic_garage(db)

    manager.check_in(
        "RJ14AB1005",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    with pytest.raises(ValueError):
        manager.check_in(
            "RJ14AB1005",
            "EV",
            datetime(2026, 9, 17, 11, 0)
        )


def test_spot_cannot_be_double_occupied(db):
    manager = ParkingManager(db)

    manager.add_spot(1, "E-101", "EV")

    first = manager.check_in(
        "RJ14AB1006",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    assert first.spot_id is not None

    with pytest.raises(ValueError):
        manager.check_in(
            "RJ14AB1007",
            "EV",
            datetime(2026, 9, 17, 10, 5)
        )


def test_vehicle_lookup_by_plate(db):
    manager = create_basic_garage(db)

    manager.check_in(
        "RJ14AB1008",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    spot = manager.get_vehicle_location("RJ14AB1008")

    assert spot is not None
    assert spot.spot_number == "E-101"
    assert spot.spot_type == "EV"


def test_unknown_vehicle_returns_none(db):
    manager = create_basic_garage(db)

    spot = manager.get_vehicle_location("RJ14UNKNOWN")

    assert spot is None


def test_checkout_releases_spot(db):
    manager = create_basic_garage(db)

    entry_time = datetime(2026, 9, 17, 10, 0)
    exit_time = datetime(2026, 9, 17, 12, 0)

    session = manager.check_in(
        "RJ14AB1009",
        "EV",
        entry_time
    )

    manager.check_out(
        "RJ14AB1009",
        exit_time
    )

    spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == session.spot_id)
        .first()
    )

    assert spot.is_occupied is False


def test_checkout_calculates_fee(db):
    manager = create_basic_garage(db)

    entry_time = datetime(2026, 9, 17, 10, 0)
    exit_time = datetime(2026, 9, 17, 12, 0)

    manager.check_in(
        "RJ14AB1010",
        "EV",
        entry_time
    )

    session = manager.check_out(
        "RJ14AB1010",
        exit_time
    )

    assert session.fee == 80.0
    assert session.is_active is False


def test_ev_availability_changes(db):
    manager = create_basic_garage(db)

    assert manager.is_ev_spot_available() is True

    manager.check_in(
        "RJ14AB1011",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    assert manager.is_ev_spot_available() is False

    manager.check_out(
        "RJ14AB1011",
        datetime(2026, 9, 17, 11, 0)
    )

    assert manager.is_ev_spot_available() is True


def test_multi_level_garage(db):
    manager = ParkingManager(db)

    manager.add_spot(1, "E-101", "EV")
    manager.add_spot(2, "E-201", "EV")

    first = manager.check_in(
        "RJ14AB1012",
        "EV",
        datetime(2026, 9, 17, 10, 0)
    )

    second = manager.check_in(
        "RJ14AB1013",
        "EV",
        datetime(2026, 9, 17, 10, 5)
    )

    first_spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == first.spot_id)
        .first()
    )

    second_spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == second.spot_id)
        .first()
    )

    assert first_spot.level == 1
    assert second_spot.level == 2


def test_duplicate_spot_number_is_rejected(db):
    manager = ParkingManager(db)

    manager.add_spot(1, "C-101", "COMPACT")

    with pytest.raises(ValueError):
        manager.add_spot(2, "C-101", "COMPACT")


def test_invalid_spot_type_is_rejected(db):
    manager = ParkingManager(db)

    with pytest.raises(ValueError):
        manager.add_spot(1, "X-101", "INVALID")


def test_invalid_vehicle_type_is_rejected(db):
    manager = create_basic_garage(db)

    with pytest.raises(ValueError):
        manager.check_in(
            "RJ14AB1014",
            "INVALID",
            datetime(2026, 9, 17, 10, 0)
        )


def test_checkout_unknown_vehicle_is_rejected(db):
    manager = create_basic_garage(db)

    with pytest.raises(ValueError):
        manager.check_out(
            "RJ14UNKNOWN",
            datetime(2026, 9, 17, 11, 0)
        )