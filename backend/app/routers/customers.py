"""Customer management endpoints (admin)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_customer_repository, require_admin_auth
from app.repositories.customers import CustomerRepository
from app.schemas.customers import CustomerItem, CustomerListResponse

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"],
    dependencies=[Depends(require_admin_auth)],
)


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    limit: int = 100,
    offset: int = 0,
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)] = None,
) -> CustomerListResponse:
    """List all customers with pagination.

    Args:
        limit: Maximum number of customers to return
        offset: Number of customers to skip
        customer_repo: Customer repository dependency

    Returns:
        List of customers with total count
    """
    customers = customer_repo.list_all_customers(limit=limit, offset=offset)
    total = customer_repo.count_customers()
    return CustomerListResponse(
        customers=[CustomerItem(**customer) for customer in customers],
        total=total,
    )
