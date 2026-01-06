from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BookingCreate(BaseModel):
    customer_id: str
    job_type: str
    scheduled_datetime: datetime
    notes: str | None = None


class BookingCreated(BaseModel):
    booking_id: str
    scheduled_datetime: datetime


