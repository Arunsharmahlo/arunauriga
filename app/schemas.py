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


class CheckOutRequest(BaseModel):
    plate_number: str = Field(min_length=1)


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