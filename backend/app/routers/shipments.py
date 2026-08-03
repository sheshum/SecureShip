"""Shipment management endpoints (admin)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_shipment_repository
from app.repositories.shipments import ShipmentRepository
from app.schemas.shipments import ShipmentItem, ShipmentListResponse

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.get("", response_model=ShipmentListResponse)
async def list_shipments(
    limit: int = 100,
    offset: int = 0,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> ShipmentListResponse:
    """List all shipments with pagination.
    
    Args:
        limit: Maximum number of shipments to return
        offset: Number of shipments to skip
        shipment_repo: Shipment repository dependency
        
    Returns:
        List of shipments with total count
    """
    shipments = shipment_repo.list_all_shipments(limit=limit, offset=offset)
    return ShipmentListResponse(
        shipments=[ShipmentItem(**ship) for ship in shipments],
        total=len(shipments),
    )


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
