from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import ParkingSpot
from .parking import ParkingManager
from .schemas import (
    CheckInRequest,
    CheckInResponse,
    CheckOutRequest,
    CheckOutResponse,
    SpotCreate,
    VehicleLocationResponse,
)


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Smart Parking Garage",
    description="Multi-level parking garage management system",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Smart Parking Garage API",
        "status": "running"
    }


@app.post("/spots")
def create_spot(
    request: SpotCreate,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    try:
        spot = manager.add_spot(
            level=request.level,
            spot_number=request.spot_number,
            spot_type=request.spot_type
        )

        return {
            "message": "Parking spot created",
            "id": spot.id,
            "level": spot.level,
            "spot_number": spot.spot_number,
            "spot_type": spot.spot_type
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.post(
    "/vehicles/check-in",
    response_model=CheckInResponse
)
def check_in(
    request: CheckInRequest,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    try:
        session = manager.check_in(
            plate_number=request.plate_number,
            vehicle_type=request.vehicle_type
        )

        spot = (
            db.query(ParkingSpot)
            .filter(ParkingSpot.id == session.spot_id)
            .first()
        )

        return CheckInResponse(
            message="Vehicle checked in successfully",
            plate_number=session.plate_number,
            vehicle_type=session.vehicle_type,
            spot_number=spot.spot_number,
            level=spot.level,
            entry_time=session.entry_time
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.post(
    "/vehicles/check-out",
    response_model=CheckOutResponse
)
def check_out(
    request: CheckOutRequest,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    try:
        session = manager.check_out(
            plate_number=request.plate_number
        )

        spot = (
            db.query(ParkingSpot)
            .filter(ParkingSpot.id == session.spot_id)
            .first()
        )

        return CheckOutResponse(
            message="Vehicle checked out successfully",
            plate_number=session.plate_number,
            spot_number=spot.spot_number,
            level=spot.level,
            entry_time=session.entry_time,
            exit_time=session.exit_time,
            fee=session.fee
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.get("/spots/ev/availability")
def ev_availability(
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    available = manager.is_ev_spot_available()

    return {
        "ev_spot_available": available
    }


@app.get(
    "/vehicles/{plate_number}",
    response_model=VehicleLocationResponse
)
def find_vehicle(
    plate_number: str,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    spot = manager.get_vehicle_location(plate_number)

    if not spot:
        raise HTTPException(
            status_code=404,
            detail="Vehicle is not currently parked"
        )

    return VehicleLocationResponse(
        plate_number=plate_number.upper(),
        spot_number=spot.spot_number,
        level=spot.level,
        spot_type=spot.spot_type
    )


@app.get("/garage/status")
def garage_status(
    db: Session = Depends(get_db)
):
    total = db.query(ParkingSpot).count()

    occupied = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.is_occupied == True)
        .count()
    )

    available = total - occupied

    ev_total = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.spot_type == "EV")
        .count()
    )

    ev_available = (
        db.query(ParkingSpot)
        .filter(
            ParkingSpot.spot_type == "EV",
            ParkingSpot.is_occupied == False
        )
        .count()
    )

    return {
        "total_spots": total,
        "occupied_spots": occupied,
        "available_spots": available,
        "ev_total": ev_total,
        "ev_available": ev_available
    }