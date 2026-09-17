from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import ParkingSpot, ParkingSession
from .pricing import calculate_fee


class ParkingManager:

    def __init__(self, db: Session):
        self.db = db

    def add_spot(
        self,
        level: int,
        spot_number: str,
        spot_type: str
    ) -> ParkingSpot:

        spot_type = spot_type.upper()

        if spot_type not in {"COMPACT", "STANDARD", "EV"}:
            raise ValueError("Invalid parking spot type")

        existing_spot = (
            self.db.query(ParkingSpot)
            .filter(ParkingSpot.spot_number == spot_number)
            .first()
        )

        if existing_spot:
            raise ValueError("Parking spot already exists")

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

        vehicle_type = vehicle_type.upper()

        if vehicle_type == "EV":
            allowed_types = ["EV"]
        elif vehicle_type == "COMPACT":
            allowed_types = ["COMPACT", "STANDARD"]
        elif vehicle_type == "STANDARD":
            allowed_types = ["STANDARD"]
        else:
            raise ValueError("Invalid vehicle type")

        return (
            self.db.query(ParkingSpot)
            .filter(
                ParkingSpot.is_occupied == False,
                ParkingSpot.spot_type.in_(allowed_types)
            )
            .order_by(
                ParkingSpot.level,
                ParkingSpot.id
            )
            .first()
        )

    def check_in(
        self,
        plate_number: str,
        vehicle_type: str,
        entry_time: Optional[datetime] = None
    ) -> ParkingSession:

        plate_number = plate_number.strip().upper()
        vehicle_type = vehicle_type.strip().upper()

        if not plate_number:
            raise ValueError("Plate number cannot be empty")

        if vehicle_type not in {"COMPACT", "STANDARD", "EV"}:
            raise ValueError("Invalid vehicle type")

        # Prevent the same vehicle from being parked twice.
        existing_vehicle = (
            self.db.query(ParkingSession)
            .filter(
                ParkingSession.plate_number == plate_number,
                ParkingSession.is_active == True
            )
            .first()
        )

        if existing_vehicle:
            raise ValueError(
                "Vehicle is already parked"
            )

        spot = self.find_available_spot(vehicle_type)

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

    def find_active_vehicle(
        self,
        plate_number: str
    ) -> Optional[ParkingSession]:

        plate_number = plate_number.strip().upper()

        return (
            self.db.query(ParkingSession)
            .filter(
                ParkingSession.plate_number == plate_number,
                ParkingSession.is_active == True
            )
            .first()
        )

    def check_out(
        self,
        plate_number: str,
        exit_time: Optional[datetime] = None
    ) -> ParkingSession:

        session = self.find_active_vehicle(plate_number)

        if not session:
            raise ValueError(
                "No active parking session found for this vehicle"
            )

        if exit_time is None:
            exit_time = datetime.now()

        if exit_time < session.entry_time:
            raise ValueError(
                "Exit time cannot be before entry time"
            )

        fee = calculate_fee(
            session.entry_time,
            exit_time
        )

        spot = (
            self.db.query(ParkingSpot)
            .filter(ParkingSpot.id == session.spot_id)
            .first()
        )

        if spot:
            spot.is_occupied = False

        session.exit_time = exit_time
        session.fee = fee
        session.is_active = False

        self.db.commit()
        self.db.refresh(session)

        return session

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

    def get_vehicle_location(
        self,
        plate_number: str
    ) -> Optional[ParkingSpot]:

        session = self.find_active_vehicle(plate_number)

        if not session:
            return None

        return (
            self.db.query(ParkingSpot)
            .filter(ParkingSpot.id == session.spot_id)
            .first()
        )