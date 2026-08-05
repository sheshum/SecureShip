"""Shipment management endpoints (admin)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_shipment_repository, require_admin_auth
from app.repositories.shipments import ShipmentRepository
from app.schemas.shipments import (
    ShipmentCreateRequest,
    ShipmentItem,
    ShipmentListResponse,
    ShipmentStatus,
    ShipmentUpdateRequest,
)

router = APIRouter(
    prefix="/api/shipments",
    tags=["shipments"],
    dependencies=[Depends(require_admin_auth)],
)


@router.get("", response_model=ShipmentListResponse)
async def list_shipments(
    limit: int = 100,
    offset: int = 0,
    status: Annotated[ShipmentStatus | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> ShipmentListResponse:
    """List all shipments with pagination.

    Args:
        limit: Maximum number of shipments to return
        offset: Number of shipments to skip
        status: Optional filter by shipment status
        q: Optional search query (tracking number, carrier)
        shipment_repo: Shipment repository dependency

    Returns:
        List of shipments with total count
    """
    shipments = shipment_repo.list_all_shipments(limit=limit, offset=offset, status=status, q=q)
    total = shipment_repo.count_shipments(status=status, q=q)
    return ShipmentListResponse(
        shipments=[ShipmentItem(**ship) for ship in shipments],
        total=total,
    )


@router.get("/search", response_model=list[ShipmentItem])
async def search_shipments(
    q: str = "",
    limit: int = 10,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> list[ShipmentItem]:
    """Typeahead search for shipments by tracking number."""
    if len(q.strip()) < 2:
        return []
    results = shipment_repo.search_shipments(q.strip(), limit=limit)
    return [ShipmentItem(**shipment) for shipment in results]


@router.get("/{shipment_id}", response_model=ShipmentItem)
async def get_shipment(
    shipment_id: UUID,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> ShipmentItem:
    """Get single shipment by ID.
    
    Args:
        shipment_id: UUID of the shipment to retrieve
        shipment_repo: Shipment repository dependency
        
    Returns:
        Shipment details
        
    Raises:
        HTTPException: 404 if shipment not found
    """
    shipment = shipment_repo.get_shipment_by_id(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return ShipmentItem(**shipment)


@router.post("", response_model=ShipmentItem, status_code=201)
async def create_shipment(
    request: ShipmentCreateRequest,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> ShipmentItem:
    """Create a new shipment."""
    shipment = shipment_repo.create_shipment(**request.model_dump())
    return ShipmentItem(**shipment)


@router.patch("/{shipment_id}", response_model=ShipmentItem)
async def update_shipment(
    shipment_id: UUID,
    request: ShipmentUpdateRequest,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> ShipmentItem:
    """Update fields on an existing shipment."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    shipment = shipment_repo.update_shipment(shipment_id, **updates)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return ShipmentItem(**shipment)


@router.delete("/{shipment_id}", status_code=204)
async def delete_shipment(
    shipment_id: UUID,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> None:
    """Delete a shipment. Fails with 409 if packages still reference it."""
    try:
        shipment = shipment_repo.delete_shipment(shipment_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
