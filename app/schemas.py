from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SpotCreate(BaseModel):
    level: int = Field(gt=0)
    spot_number: str = Field(min_length=1)
    spot_type: str


class CheckInRequest(BaseModel):
    plate_number: str = Field(min_length=1)
    vehicle_type: str
    entry_time: Optional[datetime] = None


class CheckOutRequest(BaseModel):
    plate_number: str = Field(min_length=1)
    exit_time: Optional[datetime] = None


class RateCardRequest(BaseModel):
    rates: dict


class ClockRequest(BaseModel):
    time: datetime


class TransferRequest(BaseModel):
    old_plate: str = Field(min_length=1)
    new_plate: str = Field(min_length=1)


class CheckInResponse(BaseModel):
    message: str
    plate_number: str
    vehicle_type: str
    spot_number: str
    level: int
    entry_time: datetime


class CheckOutResponse(BaseModel):
    message: str
    plate_number: str
    spot_number: str
    level: int
    entry_time: datetime
    exit_time: datetime
    fee: float


class VehicleLocationResponse(BaseModel):
    plate_number: str
    spot_number: str
    level: int
    spot_type: str


class TransferResponse(BaseModel):
    message: str
    old_plate: str
    new_plate: str
    spot_number: str
    level: int
    entry_time: datetime


class AutoCloseResponse(BaseModel):
    message: str
    closed_sessions: list


class RateCardResponse(BaseModel):
    message: str
    rates: dict