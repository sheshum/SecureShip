"""Shipment schemas for API responses."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models import SHIPMENT_STATUSES

ShipmentStatus = Literal[*SHIPMENT_STATUSES]


class ShipmentItem(BaseModel):
    id: UUID
    customer_id: UUID
    tracking_number: str
    status: str
    carrier: str
    origin: str
    destination: str
    estimated_delivery: date
    last_update: datetime
    customer_name: str | None = None
    package_count: int = 0


class ShipmentListResponse(BaseModel):
    shipments: list[ShipmentItem]
    total: int


class ShipmentCreateRequest(BaseModel):
    customer_id: UUID
    tracking_number: str
    status: ShipmentStatus
    carrier: str
    origin: str
    destination: str
    estimated_delivery: date


class ShipmentUpdateRequest(BaseModel):
    tracking_number: str | None = None
    status: ShipmentStatus | None = None
    carrier: str | None = None
    origin: str | None = None
    destination: str | None = None
    estimated_delivery: date | None = None
