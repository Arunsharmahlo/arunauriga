from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import ParkingSpot, ParkingSession
from .pricing import (
    DEFAULT_RATES,
    calculate_fee,
)


class ParkingManager:

    def __init__(self, db: Session):
        self.db = db
        self.rates = DEFAULT_RATES.copy()

    # -------------------------
    # RATE CARD
    # -------------------------

    def import_rate_card(
        self,
        rate_card: dict
    ) -> dict:

        from .pricing import clean_rate_card

        cleaned = clean_rate_card(rate_card)

        if not cleaned:
            raise ValueError(
                "No valid rates found in rate card"
            )

        self.rates.update(cleaned)

        return self.rates

    # -------------------------
    # PARKING SPOTS
    # -------------------------

    def add_spot(
        self,
        level: int,
        spot_number: str,
        spot_type: str
    ) -> ParkingSpot:

        spot_type = spot_type.strip().upper()
        spot_number = spot_number.strip()

        if spot_type not in {
            "COMPACT",
            "STANDARD",
            "EV"
        }:
            raise ValueError(
                "Invalid parking spot type"
            )

        if not spot_number:
            raise ValueError(
                "Spot number cannot be empty"
            )

        existing_spot = (
            self.db.query(ParkingSpot)
            .filter(
                ParkingSpot.spot_number
                == spot_number
            )
            .first()
        )

        if existing_spot:
            raise ValueError(
                "Parking spot already exists"
            )

        spot = ParkingSpot(
            level=level,
            spot_number=spot_number,
            spot_type=spot_type,
            is_occupied=False
        )

        self.db.add(spot)
        self.db.commit()
        self.db.refresh(spot)

        return spot

    def find_available_spot(
        self,
        vehicle_type: str
    ) -> Optional[ParkingSpot]:

        vehicle_type = vehicle_type.strip().upper()

        if vehicle_type == "EV":
            allowed_types = ["EV"]

        elif vehicle_type == "COMPACT":
            allowed_types = [
                "COMPACT",
                "STANDARD"
            ]

        elif vehicle_type == "STANDARD":
            allowed_types = ["STANDARD"]

        else:
            raise ValueError(
                "Invalid vehicle type"
            )

        return (
            self.db.query(ParkingSpot)
            .filter(
                ParkingSpot.is_occupied == False,
                ParkingSpot.spot_type.in_(
                    allowed_types
                )
            )
            .order_by(
                ParkingSpot.level,
                ParkingSpot.id
            )
            .first()
        )

    # -------------------------
    # CHECK-IN
    # -------------------------

    def check_in(
        self,
        plate_number: str,
        vehicle_type: str,
        entry_time: Optional[datetime] = None
    ) -> ParkingSession:

        plate_number = (
            plate_number.strip().upper()
        )

        vehicle_type = (
            vehicle_type.strip().upper()
        )

        if not plate_number:
            raise ValueError(
                "Plate number cannot be empty"
            )

        if vehicle_type not in {
            "COMPACT",
            "STANDARD",
            "EV"
        }:
            raise ValueError(
                "Invalid vehicle type"
            )

        existing_vehicle = (
            self.db.query(ParkingSession)
            .filter(
                ParkingSession.plate_number
                == plate_number,
                ParkingSession.is_active == True
            )
            .first()
        )

        if existing_vehicle:
            raise ValueError(
                "Vehicle is already parked"
            )

        spot = self.find_available_spot(
            vehicle_type
        )

        if not spot:
            raise ValueError(
                "No suitable parking spot available"
            )

        if entry_time is None:
            entry_time = datetime.now()

        spot.is_occupied = True

        session = ParkingSession(
            plate_number=plate_number,
            vehicle_type=vehicle_type,
            spot_id=spot.id,
            entry_time=entry_time,
            is_active=True
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    # -------------------------
    # VEHICLE LOOKUP
    # -------------------------

    def find_active_vehicle(
        self,
        plate_number: str
    ) -> Optional[ParkingSession]:

        plate_number = (
            plate_number.strip().upper()
        )

        return (
            self.db.query(ParkingSession)
            .filter(
                ParkingSession.plate_number
                == plate_number,
                ParkingSession.is_active == True
            )
            .first()
        )

    def get_vehicle_location(
        self,
        plate_number: str
    ) -> Optional[ParkingSpot]:

        session = self.find_active_vehicle(
            plate_number
        )

        if not session:
            return None

        return (
            self.db.query(ParkingSpot)
            .filter(
                ParkingSpot.id
                == session.spot_id
            )
            .first()
        )

    # -------------------------
    # CHECK-OUT
    # -------------------------

    def check_out(
        self,
        plate_number: str,
        exit_time: Optional[datetime] = None
    ) -> ParkingSession:

        session = self.find_active_vehicle(
            plate_number
        )

        if not session:
            raise ValueError(
                "No active parking session found "
                "for this vehicle"
            )

        if exit_time is None:
            exit_time = datetime.now()

        if exit_time < session.entry_time:
            raise ValueError(
                "Exit time cannot be before entry time"
            )

        spot = (
            self.db.query(ParkingSpot)
            .filter(
                ParkingSpot.id
                == session.spot_id
            )
            .first()
        )

        spot_type = (
            spot.spot_type
            if spot
            else session.vehicle_type
        )

        fee = calculate_fee(
            session.entry_time,
            exit_time,
            spot_type,
            self.rates
        )

        if spot:
            spot.is_occupied = False

        session.exit_time = exit_time
        session.fee = fee
        session.is_active = False

        self.db.commit()
        self.db.refresh(session)

        return session

    # -------------------------
    # EV AVAILABILITY
    # -------------------------

    def is_ev_spot_available(self) -> bool:

        return (
            self.db.query(ParkingSpot)
            .filter(
                ParkingSpot.spot_type == "EV",
                ParkingSpot.is_occupied == False
            )
            .first()
            is not None
        )

    # -------------------------
    # T2: CLOCK / AUTO CLOSE
    # -------------------------

    def process_clock(
        self,
        current_time: datetime
    ) -> list:

        active_sessions = (
            self.db.query(ParkingSession)
            .filter(
                ParkingSession.is_active == True
            )
            .all()
        )

        closed_sessions = []

        for session in active_sessions:

            duration = (
                current_time
                - session.entry_time
            ).total_seconds()

            if duration > 24 * 60 * 60:

                closed = self.check_out(
                    session.plate_number,
                    current_time
                )

                closed_sessions.append(
                    closed
                )

        return closed_sessions

    # -------------------------
    # T6: TRANSFER PLATE
    # -------------------------

    def transfer_session(
        self,
        old_plate: str,
        new_plate: str
    ) -> ParkingSession:

        old_plate = (
            old_plate.strip().upper()
        )

        new_plate = (
            new_plate.strip().upper()
        )

        if not old_plate or not new_plate:
            raise ValueError(
                "Plate numbers cannot be empty"
            )

        if old_plate == new_plate:
            raise ValueError(
                "New plate must be different"
            )

        session = self.find_active_vehicle(
            old_plate
        )

        if not session:
            raise ValueError(
                "No active session found "
                "for old plate"
            )

        existing_new_plate = (
            self.find_active_vehicle(
                new_plate
            )
        )

        if existing_new_plate:
            raise ValueError(
                "New plate is already parked"
            )

        session.plate_number = new_plate

        self.db.commit()
        self.db.refresh(session)

        return session