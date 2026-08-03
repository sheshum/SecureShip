"""Shipment schemas for API responses."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


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
