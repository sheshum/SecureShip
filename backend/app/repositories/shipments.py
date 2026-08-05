"""Read-only shipment data access used by LLM tools."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionLocal
from app.models import Customer, Package, Shipment


class ShipmentRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def create_shipment(self, **fields: object) -> dict:
        with self._session_factory() as session:
            shipment = Shipment(**fields, last_update=datetime.now(UTC))
            session.add(shipment)
            session.commit()
            session.refresh(shipment, attribute_names=["packages", "customer"])
            return self._serialize_shipment_with_customer(shipment)

    def update_shipment(self, shipment_id: UUID, **updates: object) -> dict | None:
        with self._session_factory() as session:
            shipment = session.get(
                Shipment, shipment_id, options=[selectinload(Shipment.packages), selectinload(Shipment.customer)]
            )
            if shipment is None:
                return None
            for key, value in updates.items():
                setattr(shipment, key, value)
            shipment.last_update = datetime.now(UTC)
            session.commit()
            session.refresh(shipment, attribute_names=["packages", "customer"])
            return self._serialize_shipment_with_customer(shipment)

    def delete_shipment(self, shipment_id: UUID) -> dict | None:
        with self._session_factory() as session:
            shipment = session.get(
                Shipment, shipment_id, options=[selectinload(Shipment.packages), selectinload(Shipment.customer)]
            )
            if shipment is None:
                return None
            package_count = session.scalar(
                select(func.count()).select_from(Package).where(Package.shipment_id == shipment_id)
            )
            if package_count:
                msg = f"Cannot delete shipment: {package_count} package(s) still reference this shipment"
                raise ValueError(msg)
            serialized = self._serialize_shipment_with_customer(shipment)
            session.delete(shipment)
            session.commit()
            return serialized

    def get_shipment_by_tracking_number_for_customer(
        self,
        tracking_number: str,
        customer_id: UUID | str,
    ) -> dict | None:
        customer_uuid = UUID(str(customer_id))
        with self._session_factory() as session:
            shipment = session.scalar(
                select(Shipment)
                .options(selectinload(Shipment.packages), selectinload(Shipment.customer))
                .where(
                    Shipment.tracking_number == tracking_number,
                    Shipment.customer_id == customer_uuid,
                )
            )
            if shipment is None:
                return None
            return self._serialize_shipment(shipment)

    def get_shipments_for_customer(self, customer_id: UUID | str) -> dict:
        customer_uuid = UUID(str(customer_id))
        customer_id_value = str(customer_uuid)
        with self._session_factory() as session:
            customer = session.get(Customer, customer_uuid)
            if customer is None:
                return {
                    "found": False,
                    "customer_id": customer_id_value,
                    "shipments": [],
                }

            shipments = session.scalars(
                select(Shipment)
                .options(selectinload(Shipment.packages), selectinload(Shipment.customer))
                .where(Shipment.customer_id == customer_uuid)
                .order_by(Shipment.last_update.desc())
            ).all()

            return {
                "found": True,
                "customer": self._serialize_customer(customer),
                "shipments": [self._serialize_shipment(shipment) for shipment in shipments],
            }

    def list_shipments_for_customer(
        self,
        customer_id: UUID | str,
        tracking_number: str | None = None,
    ) -> list[Shipment]:
        """List shipments for a customer, optionally filtered by tracking number.

        Returns raw Shipment models (not serialized) for tool use.
        Used by LLM tools that need to apply custom serialization.
        """
        customer_uuid = UUID(str(customer_id))
        with self._session_factory() as session:
            stmt = (
                select(Shipment)
                .options(selectinload(Shipment.packages))
                .where(Shipment.customer_id == customer_uuid)
            )

            if tracking_number:
                stmt = stmt.where(Shipment.tracking_number == tracking_number)

            stmt = stmt.order_by(Shipment.last_update.desc())

            return session.scalars(stmt).all()

    def list_all_shipments(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List all shipments with pagination (admin view)."""
        with self._session_factory() as session:
            shipments = session.scalars(
                select(Shipment)
                .options(selectinload(Shipment.packages), selectinload(Shipment.customer))
                .order_by(Shipment.last_update.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._serialize_shipment_with_customer(ship) for ship in shipments]

    def count_shipments(self) -> int:
        """Return total count of all shipments."""
        with self._session_factory() as session:
            return session.scalar(select(func.count()).select_from(Shipment)) or 0

    def get_shipment_by_tracking_number(self, tracking_number: str) -> dict | None:
        """Get single shipment by tracking number, unscoped by customer (admin view)."""
        with self._session_factory() as session:
            shipment = session.scalar(
                select(Shipment)
                .options(selectinload(Shipment.packages), selectinload(Shipment.customer))
                .where(Shipment.tracking_number == tracking_number)
            )
            if shipment is None:
                return None
            return self._serialize_shipment_with_customer(shipment)

    def search_shipments(self, query: str, limit: int = 10) -> list[dict]:
        """Partial, case-insensitive search by tracking number (admin view)."""
        pattern = f"%{query}%"
        with self._session_factory() as session:
            shipments = session.scalars(
                select(Shipment)
                .options(selectinload(Shipment.packages), selectinload(Shipment.customer))
                .where(Shipment.tracking_number.ilike(pattern))
                .order_by(Shipment.last_update.desc())
                .limit(limit)
            ).all()
            return [self._serialize_shipment_with_customer(ship) for ship in shipments]

    def get_shipment_by_id(self, shipment_id: UUID) -> dict | None:
        """Get single shipment by ID (admin view)."""
        with self._session_factory() as session:
            shipment = session.scalar(
                select(Shipment)
                .options(selectinload(Shipment.packages), selectinload(Shipment.customer))
                .where(Shipment.id == shipment_id)
            )
            if shipment is None:
                return None
            return self._serialize_shipment_with_customer(shipment)

    @staticmethod
    def _serialize_customer(customer: Customer) -> dict:
        return {
            "id": str(customer.id),
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone_number": customer.phone_number,
            "address": customer.address,
        }


    @classmethod
    def _serialize_shipment_with_customer(cls, shipment: Shipment) -> dict:
        """Serialize shipment with customer name for admin views."""
        customer_name = None
        if shipment.customer:
            customer_name = f"{shipment.customer.first_name} {shipment.customer.last_name}"
        
        return {
            "id": str(shipment.id),
            "customer_id": str(shipment.customer_id),
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "carrier": shipment.carrier,
            "origin": shipment.origin,
            "destination": shipment.destination,
            "estimated_delivery": shipment.estimated_delivery.isoformat(),
            "last_update": shipment.last_update.isoformat(),
            "customer_name": customer_name,
            "package_count": len(shipment.packages) if shipment.packages else 0,
        }
    @classmethod
    def _serialize_shipment(cls, shipment: Shipment) -> dict:
        return {
            "id": str(shipment.id),
            "customer_id": str(shipment.customer_id),
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "carrier": shipment.carrier,
            "origin": shipment.origin,
            "destination": shipment.destination,
            "estimated_delivery": shipment.estimated_delivery.isoformat(),
            "last_update": shipment.last_update.isoformat(),
            "packages": [cls._serialize_package(package) for package in shipment.packages],
        }

    @staticmethod
    def _serialize_package(package: Package) -> dict:
        return {
            "id": str(package.id),
            "shipment_id": str(package.shipment_id),
            "description": package.description,
            "weight_kg": str(package.weight_kg),
            "declared_value": str(package.declared_value),
        }
