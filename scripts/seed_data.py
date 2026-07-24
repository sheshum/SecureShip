"""Seed the SecureShip database with AI-generated mock data.

Conforms to the shared schema in SecureShip-5Week-Program.md section 4.4:
25+ customers, 40-60 shipments with a realistic status distribution
(mostly in_transit/delivered, a few exceptions), 1+ packages per shipment.

Usage (from the repo root):
    cd backend && uv run python ../scripts/seed_data.py

Connects via DATABASE_URL (defaults to the docker-compose Postgres on
localhost:5432). Re-running truncates and re-seeds; a fixed random seed
makes the generated data reproducible.
"""

import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from faker import Faker
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db import SessionLocal  # noqa: E402
from app.models import Customer, Package, Shipment  # noqa: E402

SEED = 20260724
NUM_CUSTOMERS = 30
NUM_SHIPMENTS = 50

# Most shipments in_transit/delivered, a few exceptions to give the
# chat something interesting to discuss (program spec 4.4).
STATUS_WEIGHTS = {
    "in_transit": 40,
    "delivered": 35,
    "out_for_delivery": 10,
    "label_created": 8,
    "exception": 7,
}

CARRIERS = {
    "MockExpress": "MEX",
    "ShipFast Logistics": "SFL",
    "GlobalParcel": "GPL",
    "TransEuro Freight": "TEF",
}

CITIES = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Seattle, WA",
    "Miami, FL",
    "Denver, CO",
    "Boston, MA",
    "Berlin, DE",
    "Paris, FR",
    "Amsterdam, NL",
    "Madrid, ES",
]

PACKAGE_DESCRIPTIONS = [
    "Books and printed media",
    "Consumer electronics",
    "Clothing and apparel",
    "Kitchen appliances",
    "Sporting goods",
    "Office supplies",
    "Toys and games",
    "Home decor",
    "Automotive parts",
    "Cosmetics and skincare",
    "Board games",
    "Musical instrument accessories",
]

# Fixed "now" so reruns with the same seed produce identical rows.
NOW = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)

fake = Faker("en_US")
Faker.seed(SEED)
random.seed(SEED)


def make_customers() -> list[Customer]:
    return [
        Customer(
            id=uuid.UUID(int=random.getrandbits(128), version=4),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            phone_number=f"+1{random.randint(2_000_000_000, 9_899_999_999)}",
            address=(
                f"{fake.building_number()} {fake.street_name()}, "
                f"{fake.city()}, {fake.state_abbr()} {fake.postcode()}"
            ),
        )
        for _ in range(NUM_CUSTOMERS)
    ]


def make_tracking_number(prefix: str) -> str:
    return f"{prefix}-{random.randint(0, 999_999_999_999):012d}"


def make_statuses(count: int) -> list[str]:
    """Weighted-random statuses with a guaranteed handful of exceptions."""
    statuses = random.choices(
        list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values()), k=count
    )
    while statuses.count("exception") < 3:
        statuses[random.randrange(count)] = "exception"
    random.shuffle(statuses)
    return statuses


def make_shipment(customer: Customer, status: str) -> Shipment:
    carrier, prefix = random.choice(list(CARRIERS.items()))
    origin, destination = random.sample(CITIES, 2)

    # Keep dates consistent with the status.
    if status == "delivered":
        eta = NOW.date() - timedelta(days=random.randint(1, 30))
        last_update = datetime.combine(
            eta - timedelta(days=random.randint(0, 2)),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ) + timedelta(hours=random.randint(8, 20))
    elif status == "label_created":
        eta = NOW.date() + timedelta(days=random.randint(5, 14))
        last_update = NOW - timedelta(hours=random.randint(1, 48))
    elif status == "out_for_delivery":
        eta = NOW.date()
        last_update = NOW - timedelta(hours=random.randint(1, 8))
    else:  # in_transit or exception
        eta = NOW.date() + timedelta(days=random.randint(1, 10))
        last_update = NOW - timedelta(hours=random.randint(2, 72))

    return Shipment(
        id=uuid.UUID(int=random.getrandbits(128), version=4),
        customer_id=customer.id,
        tracking_number=make_tracking_number(prefix),
        status=status,
        carrier=carrier,
        origin=origin,
        destination=destination,
        estimated_delivery=eta,
        last_update=last_update,
    )


def make_packages(shipment: Shipment) -> list[Package]:
    return [
        Package(
            id=uuid.UUID(int=random.getrandbits(128), version=4),
            shipment_id=shipment.id,
            description=random.choice(PACKAGE_DESCRIPTIONS),
            weight_kg=Decimal(random.randint(20, 2500)) / 100,
            declared_value=Decimal(random.randint(500, 150_000)) / 100,
        )
        for _ in range(random.choices([1, 2, 3], weights=[60, 30, 10])[0])
    ]


def main() -> None:
    customers = make_customers()
    shipments = [
        make_shipment(random.choice(customers), status)
        for status in make_statuses(NUM_SHIPMENTS)
    ]
    packages = [pkg for shp in shipments for pkg in make_packages(shp)]

    statuses = {s: 0 for s in STATUS_WEIGHTS}
    for shp in shipments:
        statuses[shp.status] += 1

    with SessionLocal() as session:
        session.execute(
            text("TRUNCATE package, shipment, chat_session, customer CASCADE")
        )
        session.add_all(customers)
        session.add_all(shipments)
        session.add_all(packages)
        session.commit()

    print(
        f"Seeded {len(customers)} customers, {len(shipments)} shipments, "
        f"{len(packages)} packages."
    )
    print(f"Status distribution: {statuses}")


if __name__ == "__main__":
    main()
