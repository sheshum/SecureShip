"""Read-only customer data access for identity verification flows."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Customer, Shipment


class CustomerRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def get_customer_by_id(self, customer_id: UUID) -> dict | None:
        """Get single customer by ID (admin view)."""
        with self._session_factory() as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                return None
            return self._serialize_customer(customer)

    def create_customer(
        self, *, first_name: str, last_name: str, phone_number: str, address: str
    ) -> dict:
        with self._session_factory() as session:
            customer = Customer(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                address=address,
            )
            session.add(customer)
            session.commit()
            session.refresh(customer)
            return self._serialize_customer(customer)

    def update_customer(self, customer_id: UUID, **updates: object) -> dict | None:
        with self._session_factory() as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                return None
            for key, value in updates.items():
                setattr(customer, key, value)
            session.commit()
            session.refresh(customer)
            return self._serialize_customer(customer)

    def delete_customer(self, customer_id: UUID) -> dict | None:
        with self._session_factory() as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                return None
            shipment_count = session.scalar(
                select(func.count()).select_from(Shipment).where(Shipment.customer_id == customer_id)
            )
            if shipment_count:
                msg = f"Cannot delete customer: {shipment_count} shipment(s) still reference this customer"
                raise ValueError(msg)
            serialized = self._serialize_customer(customer)
            session.delete(customer)
            session.commit()
            return serialized

    def list_all_customers(self, limit: int = 100, offset: int = 0, q: str | None = None) -> list[dict]:
        with self._session_factory() as session:
            stmt = select(Customer).order_by(Customer.last_name, Customer.first_name)
            if q is not None:
                pattern = f"%{q}%"
                stmt = stmt.where(
                    or_(
                        Customer.first_name.ilike(pattern),
                        Customer.last_name.ilike(pattern),
                        func.concat(Customer.first_name, " ", Customer.last_name).ilike(pattern),
                        Customer.phone_number.ilike(pattern),
                        Customer.address.ilike(pattern),
                    )
                )
            customers = session.scalars(stmt.limit(limit).offset(offset)).all()
            return [self._serialize_customer(customer) for customer in customers]

    def count_customers(self, q: str | None = None) -> int:
        with self._session_factory() as session:
            query = select(func.count()).select_from(Customer)
            if q is not None:
                pattern = f"%{q}%"
                query = query.where(
                    or_(
                        Customer.first_name.ilike(pattern),
                        Customer.last_name.ilike(pattern),
                        func.concat(Customer.first_name, " ", Customer.last_name).ilike(pattern),
                        Customer.phone_number.ilike(pattern),
                        Customer.address.ilike(pattern),
                    )
                )
            return session.scalar(query) or 0

    def search_customers(self, query: str, limit: int = 10) -> list[dict]:
        """Partial, case-insensitive search by first/last name or phone number."""
        pattern = f"%{query}%"
        with self._session_factory() as session:
            customers = session.scalars(
                select(Customer)
                .where(
                    or_(
                        Customer.first_name.ilike(pattern),
                        Customer.last_name.ilike(pattern),
                        Customer.phone_number.ilike(pattern),
                    )
                )
                .order_by(Customer.last_name, Customer.first_name)
                .limit(limit)
            ).all()
            return [self._serialize_customer(customer) for customer in customers]

    def list_customers_by_name(self, first_name: str, last_name: str) -> list[dict]:
        with self._session_factory() as session:
            customers = session.scalars(
                select(Customer)
                .where(func.lower(Customer.first_name) == first_name)
                .where(func.lower(Customer.last_name) == last_name)
            ).all()
            return [self._serialize_customer(customer) for customer in customers]

    def find_by_identity(
        self, first_name: str, last_name: str, phone_number: str
    ) -> Customer | None:
        """Find customer by name and phone (case-insensitive name match).

        Used by identity verification to match customer records.
        Returns the actual Customer model (not serialized) for tool use.
        """
        with self._session_factory() as session:
            result = session.execute(
                select(Customer).where(
                    func.lower(Customer.first_name) == first_name.lower(),
                    func.lower(Customer.last_name) == last_name.lower(),
                    Customer.phone_number == phone_number,
                )
            )
            return result.scalar_one_or_none()

    @staticmethod
    def _serialize_customer(customer: Customer) -> dict:
        return {
            "id": str(customer.id),
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone_number": customer.phone_number,
            "address": customer.address,
        }
