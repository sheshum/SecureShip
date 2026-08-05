"""Read-only customer data access for identity verification flows."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Customer


class CustomerRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def list_all_customers(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self._session_factory() as session:
            customers = session.scalars(
                select(Customer)
                .order_by(Customer.last_name, Customer.first_name)
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._serialize_customer(customer) for customer in customers]

    def count_customers(self) -> int:
        with self._session_factory() as session:
            return session.scalar(select(func.count()).select_from(Customer)) or 0

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
