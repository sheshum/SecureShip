"""Customer schemas for API responses."""

from uuid import UUID

from pydantic import BaseModel


class CustomerItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone_number: str
    address: str


class CustomerListResponse(BaseModel):
    customers: list[CustomerItem]
    total: int


class CustomerCreateRequest(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    address: str


class CustomerUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    address: str | None = None
