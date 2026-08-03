"""Read-only package data access for admin views."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionLocal
from app.models import Package


class PackageRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def list_packages(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List all packages with pagination (admin view)."""
        with self._session_factory() as session:
            packages = session.scalars(
                select(Package)
                .options(selectinload(Package.shipment))
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._serialize_package(pkg) for pkg in packages]

    def count_packages(self) -> int:
        """Return total count of all packages."""
        with self._session_factory() as session:
            from sqlalchemy import func
            return session.scalar(select(func.count()).select_from(Package)) or 0

    def get_package(self, package_id: UUID) -> dict | None:
        """Get single package by ID (admin view)."""
        with self._session_factory() as session:
            package = session.scalar(
                select(Package)
                .options(selectinload(Package.shipment))
                .where(Package.id == package_id)
            )
            if package is None:
                return None
            return self._serialize_package(package)

    def list_packages_by_shipment(self, shipment_id: UUID) -> list[dict]:
        """List all packages for a specific shipment."""
        with self._session_factory() as session:
            packages = session.scalars(
                select(Package)
                .options(selectinload(Package.shipment))
                .where(Package.shipment_id == shipment_id)
            ).all()
            return [self._serialize_package(pkg) for pkg in packages]

    @staticmethod
    def _serialize_package(package: Package) -> dict:
        """Serialize package with shipment tracking number for display."""
        return {
            "id": str(package.id),
            "shipment_id": str(package.shipment_id),
            "description": package.description,
            "weight_kg": str(package.weight_kg),
            "declared_value": str(package.declared_value),
            "shipment_tracking_number": package.shipment.tracking_number if package.shipment else None,
        }
