"""Customer management endpoints (admin)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_customer_repository, require_admin_auth
from app.repositories.customers import CustomerRepository
from app.schemas.customers import (
    CustomerCreateRequest,
    CustomerItem,
    CustomerListResponse,
    CustomerUpdateRequest,
)

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"],
    dependencies=[Depends(require_admin_auth)],
)


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    limit: int = 100,
    offset: int = 0,
    q: Annotated[str | None, Query()] = None,
    customer_id: Annotated[UUID | None, Query()] = None,
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)] = None,
) -> CustomerListResponse:
    """List all customers with pagination.

    Args:
        limit: Maximum number of customers to return
        offset: Number of customers to skip
        q: Optional search query (name, phone, address)
        customer_id: Optional filter by exact customer UUID
        customer_repo: Customer repository dependency

    Returns:
        List of customers with total count
    """
    customers = customer_repo.list_all_customers(limit=limit, offset=offset, q=q, customer_id=customer_id)
    total = customer_repo.count_customers(q=q, customer_id=customer_id)
    return CustomerListResponse(
        customers=[CustomerItem(**customer) for customer in customers],
        total=total,
    )


@router.get("/search", response_model=list[CustomerItem])
async def search_customers(
    q: str = "",
    limit: int = 10,
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)] = None,
) -> list[CustomerItem]:
    """Typeahead search for customers by first/last name or phone number."""
    if len(q.strip()) < 2:
        return []
    results = customer_repo.search_customers(q.strip(), limit=limit)
    return [CustomerItem(**customer) for customer in results]


@router.post("", response_model=CustomerItem, status_code=201)
async def create_customer(
    request: CustomerCreateRequest,
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)] = None,
) -> CustomerItem:
    """Create a new customer."""
    customer = customer_repo.create_customer(**request.model_dump())
    return CustomerItem(**customer)


@router.patch("/{customer_id}", response_model=CustomerItem)
async def update_customer(
    customer_id: UUID,
    request: CustomerUpdateRequest,
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)] = None,
) -> CustomerItem:
    """Update fields on an existing customer."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    customer = customer_repo.update_customer(customer_id, **updates)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return CustomerItem(**customer)


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: UUID,
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)] = None,
) -> None:
    """Delete a customer. Fails with 409 if shipments still reference it."""
    try:
        customer = customer_repo.delete_customer(customer_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
