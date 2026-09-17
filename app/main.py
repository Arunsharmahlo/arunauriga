from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import ParkingSpot
from .parking import ParkingManager
from .schemas import (
    AutoCloseResponse,
    CheckInRequest,
    CheckInResponse,
    CheckOutRequest,
    CheckOutResponse,
    ClockRequest,
    RateCardRequest,
    RateCardResponse,
    SpotCreate,
    TransferRequest,
    TransferResponse,
    VehicleLocationResponse,
)


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Smart Parking Garage",
    description=(
        "Multi-level parking garage management "
        "system with pricing, automation and "
        "vehicle lifecycle management"
    ),
    version="2.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Smart Parking Garage API",
        "status": "running"
    }


# -------------------------
# PARKING SPOTS
# -------------------------

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


# -------------------------
# RATE CARD - T4
# -------------------------

@app.post(
    "/rate-card",
    response_model=RateCardResponse
)
def import_rate_card(
    request: RateCardRequest,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    try:
        rates = manager.import_rate_card(
            request.rates
        )

        return RateCardResponse(
            message="Rate card imported and cleaned",
            rates=rates
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# -------------------------
# CHECK-IN
# -------------------------

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
            vehicle_type=request.vehicle_type,
            entry_time=request.entry_time
        )

        spot = (
            db.query(ParkingSpot)
            .filter(
                ParkingSpot.id
                == session.spot_id
            )
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


# -------------------------
# CHECK-OUT
# -------------------------

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
            plate_number=request.plate_number,
            exit_time=request.exit_time
        )

        spot = (
            db.query(ParkingSpot)
            .filter(
                ParkingSpot.id
                == session.spot_id
            )
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


# -------------------------
# EV AVAILABILITY
# -------------------------

@app.get("/spots/ev/availability")
def ev_availability(
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    return {
        "ev_spot_available":
            manager.is_ev_spot_available()
    }


# -------------------------
# VEHICLE LOOKUP
# -------------------------

@app.get(
    "/vehicles/{plate_number}",
    response_model=VehicleLocationResponse
)
def find_vehicle(
    plate_number: str,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    spot = manager.get_vehicle_location(
        plate_number
    )

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


# -------------------------
# GARAGE STATUS
# -------------------------

@app.get("/garage/status")
def garage_status(
    db: Session = Depends(get_db)
):
    total = (
        db.query(ParkingSpot).count()
    )

    occupied = (
        db.query(ParkingSpot)
        .filter(
            ParkingSpot.is_occupied == True
        )
        .count()
    )

    available = total - occupied

    ev_total = (
        db.query(ParkingSpot)
        .filter(
            ParkingSpot.spot_type == "EV"
        )
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


# -------------------------
# T2 - CLOCK AUTOMATION
# -------------------------

@app.post(
    "/clock",
    response_model=AutoCloseResponse
)
def clock(
    request: ClockRequest,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    try:
        closed = manager.process_clock(
            request.time
        )

        results = []

        for session in closed:
            results.append({
                "plate_number":
                    session.plate_number,
                "exit_time":
                    session.exit_time,
                "fee":
                    session.fee,
                "spot_id":
                    session.spot_id
            })

        return AutoCloseResponse(
            message=(
                f"Automatically closed "
                f"{len(results)} session(s)"
            ),
            closed_sessions=results
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# -------------------------
# T6 - TRANSFER SESSION
# -------------------------

@app.post(
    "/vehicles/transfer",
    response_model=TransferResponse
)
def transfer_vehicle(
    request: TransferRequest,
    db: Session = Depends(get_db)
):
    manager = ParkingManager(db)

    try:
        session = manager.transfer_session(
            old_plate=request.old_plate,
            new_plate=request.new_plate
        )

        spot = (
            db.query(ParkingSpot)
            .filter(
                ParkingSpot.id
                == session.spot_id
            )
            .first()
        )

        return TransferResponse(
            message="Parking session transferred successfully",
            old_plate=request.old_plate.upper(),
            new_plate=session.plate_number,
            spot_number=spot.spot_number,
            level=spot.level,
            entry_time=session.entry_time
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )