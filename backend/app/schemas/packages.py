"""Package schemas for API responses."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PackageItem(BaseModel):
    id: UUID
    shipment_id: UUID
    description: str
    weight_kg: Decimal
    declared_value: Decimal
    shipment_tracking_number: str | None = None


class PackageListResponse(BaseModel):
    packages: list[PackageItem]
    total: int


class PackageCreateRequest(BaseModel):
    tracking_number: str
    description: str
    weight_kg: Decimal
    declared_value: Decimal


class PackageUpdateRequest(BaseModel):
    description: str | None = None
    weight_kg: Decimal | None = None
    declared_value: Decimal | None = None
