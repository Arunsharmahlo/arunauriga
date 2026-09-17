from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Float
from .database import Base


class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, nullable=False)
    spot_number = Column(String, nullable=False, unique=True)
    spot_type = Column(String, nullable=False)
    is_occupied = Column(Boolean, default=False, nullable=False)


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, nullable=False, index=True)
    vehicle_type = Column(String, nullable=False)
    spot_id = Column(Integer, nullable=False)

    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)

    fee = Column(Float, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)