"""Package management endpoints (admin)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_package_repository
from app.repositories.packages import PackageRepository
from app.schemas.packages import PackageItem, PackageListResponse

router = APIRouter(prefix="/api/packages", tags=["packages"])


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
