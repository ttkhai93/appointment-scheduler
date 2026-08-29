"""Idempotent developer seed data.

Usage: uv run python -m app.seed
"""

import asyncio
import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Dealership,
    ServiceBay,
    ServiceType,
    Technician,
    TechnicianQualification,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEALERSHIP = {
    "name": "Saigon Auto Service",
    "address": "12 Nguyen Hue, District 1, Ho Chi Minh City",
    "timezone": "Asia/Ho_Chi_Minh",
}

SERVICE_TYPES = [
    {
        "name": "Oil Change",
        "description": "Engine oil and filter replacement",
        "duration_minutes": 60,
    },
    {
        "name": "Tire Rotation",
        "description": "Rotate tires and check pressure",
        "duration_minutes": 60,
    },
    {
        "name": "Brake Inspection",
        "description": "Inspect pads, rotors, and brake fluid",
        "duration_minutes": 60,
    },
    {
        "name": "AC Service",
        "description": "AC performance check and refrigerant top-up",
        "duration_minutes": 60,
    },
    {
        "name": "Full Service",
        "description": "Comprehensive 50-point inspection",
        "duration_minutes": 120,
    },
]

TECHNICIANS = [
    {
        "name": "Anh Tuan",
        "service_types": [
            "Oil Change",
            "Tire Rotation",
            "Brake Inspection",
            "Full Service",
        ],
    },
    {
        "name": "Bao Linh",
        "service_types": ["Oil Change", "AC Service"],
    },
    {
        "name": "Chi Dung",
        "service_types": ["Tire Rotation", "Brake Inspection", "Full Service"],
    },
    {
        "name": "Duc Huy",
        "service_types": [
            "Oil Change",
            "Tire Rotation",
            "AC Service",
            "Full Service",
        ],
    },
]

SERVICE_BAYS = ["Bay 1", "Bay 2", "Bay 3"]


async def seed() -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(select(Dealership).limit(1))
        if existing is not None:
            logger.info("seed data already present; skipping")
            return

        dealership = Dealership(**DEALERSHIP)
        session.add(dealership)
        await session.flush()

        service_types: dict[str, ServiceType] = {}
        for spec in SERVICE_TYPES:
            service_type = ServiceType(
                name=spec["name"],
                description=spec["description"],
                duration_minutes=spec["duration_minutes"],
            )
            session.add(service_type)
            service_types[spec["name"]] = service_type
        await session.flush()

        for spec in TECHNICIANS:
            technician = Technician(
                dealership_id=dealership.id,
                name=spec["name"],
            )
            session.add(technician)
            await session.flush()
            for service_name in spec["service_types"]:
                session.add(
                    TechnicianQualification(
                        technician_id=technician.id,
                        service_type_id=service_types[service_name].id,
                    )
                )

        for name in SERVICE_BAYS:
            session.add(ServiceBay(dealership_id=dealership.id, name=name))

        await session.commit()
        logger.info(
            "seeded %r (%s) with %d service types, %d technicians, %d bays",
            dealership.name,
            dealership.timezone,
            len(service_types),
            len(TECHNICIANS),
            len(SERVICE_BAYS),
        )


if __name__ == "__main__":
    asyncio.run(seed())
