"""Package management endpoints (admin)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_package_repository, get_shipment_repository, require_admin_auth
from app.repositories.packages import PackageRepository
from app.repositories.shipments import ShipmentRepository
from app.schemas.packages import (
    PackageCreateRequest,
    PackageItem,
    PackageListResponse,
    PackageUpdateRequest,
)

router = APIRouter(
    prefix="/api/packages",
    tags=["packages"],
    dependencies=[Depends(require_admin_auth)],
)


@router.get("", response_model=PackageListResponse)
async def list_packages(
    limit: int = 100,
    offset: int = 0,
    package_repo: Annotated[PackageRepository, Depends(get_package_repository)] = None,
) -> PackageListResponse:
    """List all packages with pagination.
    
    Args:
        limit: Maximum number of packages to return
        offset: Number of packages to skip
        package_repo: Package repository dependency
        
    Returns:
        List of packages with total count
    """
    packages = package_repo.list_packages(limit=limit, offset=offset)
    total = package_repo.count_packages()
    return PackageListResponse(
        packages=[PackageItem(**pkg) for pkg in packages],
        total=total,
    )


@router.get("/{package_id}", response_model=PackageItem)
async def get_package(
    package_id: UUID,
    package_repo: Annotated[PackageRepository, Depends(get_package_repository)] = None,
) -> PackageItem:
    """Get single package by ID.
    
    Args:
        package_id: UUID of the package to retrieve
        package_repo: Package repository dependency
        
    Returns:
        Package details
        
    Raises:
        HTTPException: 404 if package not found
    """
    package = package_repo.get_package(package_id)
    if package is None:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    return PackageItem(**package)


@router.get("/by-shipment/{shipment_id}", response_model=PackageListResponse)
async def list_packages_by_shipment(
    shipment_id: UUID,
    package_repo: Annotated[PackageRepository, Depends(get_package_repository)] = None,
) -> PackageListResponse:
    """List all packages for a specific shipment.
    
    Args:
        shipment_id: UUID of the shipment
        package_repo: Package repository dependency
        
    Returns:
        List of packages for the shipment
    """
    packages = package_repo.list_packages_by_shipment(shipment_id)
    return PackageListResponse(
        packages=[PackageItem(**pkg) for pkg in packages],
        total=len(packages),
    )


@router.post("", response_model=PackageItem, status_code=201)
async def create_package(
    request: PackageCreateRequest,
    package_repo: Annotated[PackageRepository, Depends(get_package_repository)] = None,
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)] = None,
) -> PackageItem:
    """Create a new package, resolving its shipment by tracking number."""
    shipment = shipment_repo.get_shipment_by_tracking_number(request.tracking_number)
    if shipment is None:
        raise HTTPException(
            status_code=404,
            detail=f"No shipment found with tracking number {request.tracking_number}",
        )
    package = package_repo.create_package(
        shipment_id=shipment["id"],
        description=request.description,
        weight_kg=request.weight_kg,
        declared_value=request.declared_value,
    )
    return PackageItem(**package)


@router.patch("/{package_id}", response_model=PackageItem)
async def update_package(
    package_id: UUID,
    request: PackageUpdateRequest,
    package_repo: Annotated[PackageRepository, Depends(get_package_repository)] = None,
) -> PackageItem:
    """Update fields on an existing package."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    package = package_repo.update_package(package_id, **updates)
    if package is None:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    return PackageItem(**package)


@router.delete("/{package_id}", status_code=204)
async def delete_package(
    package_id: UUID,
    package_repo: Annotated[PackageRepository, Depends(get_package_repository)] = None,
) -> None:
    """Delete a package."""
    package = package_repo.delete_package(package_id)
    if package is None:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
