import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application import create_app
from app.database import Base
from app.dependencies import get_db
from app.models import (
    Dealership,
    ServiceBay,
    ServiceType,
    Technician,
    TechnicianQualification,
)

TEST_DB_NAME = "appointment_scheduler_test"
ADMIN_DSN = "postgresql://postgres:postgres@localhost:5433/postgres"
TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/appointment_scheduler_test"
)


async def seed_reference_data(session) -> None:
    dealership = Dealership(
        name="Saigon Auto Service",
        address="12 Nguyen Hue, District 1, Ho Chi Minh City",
        timezone="Asia/Ho_Chi_Minh",
    )
    session.add(dealership)
    await session.flush()

    oil = ServiceType(
        name="Oil Change",
        description="Engine oil and filter replacement",
        duration_minutes=60,
    )
    tire = ServiceType(
        name="Tire Rotation",
        description="Rotate tires and check pressure",
        duration_minutes=60,
    )
    full = ServiceType(
        name="Full Service",
        description="Comprehensive 50-point inspection",
        duration_minutes=120,
    )
    # No technician is qualified for this service type (negative path).
    diagnostics = ServiceType(
        name="Engine Diagnostics",
        description="No technician qualified in the seed data",
        duration_minutes=60,
    )
    session.add_all([oil, tire, full, diagnostics])
    await session.flush()

    technicians = [
        Technician(dealership_id=dealership.id, name="Anh Tuan"),
        Technician(dealership_id=dealership.id, name="Bao Linh"),
        Technician(dealership_id=dealership.id, name="Chi Dung"),
        Technician(dealership_id=dealership.id, name="Duc Huy"),
    ]
    session.add_all(technicians)
    await session.flush()

    session.add_all(
        [
            TechnicianQualification(
                technician_id=technicians[0].id, service_type_id=oil.id
            ),
            TechnicianQualification(
                technician_id=technicians[0].id, service_type_id=tire.id
            ),
            TechnicianQualification(
                technician_id=technicians[0].id, service_type_id=full.id
            ),
            TechnicianQualification(
                technician_id=technicians[1].id, service_type_id=oil.id
            ),
            TechnicianQualification(
                technician_id=technicians[2].id, service_type_id=full.id
            ),
            TechnicianQualification(
                technician_id=technicians[2].id, service_type_id=tire.id
            ),
            TechnicianQualification(
                technician_id=technicians[3].id, service_type_id=oil.id
            ),
            TechnicianQualification(
                technician_id=technicians[3].id, service_type_id=full.id
            ),
        ]
    )
    session.add_all(
        [
            ServiceBay(dealership_id=dealership.id, name="Bay 1"),
            ServiceBay(dealership_id=dealership.id, name="Bay 2"),
            ServiceBay(dealership_id=dealership.id, name="Bay 3"),
        ]
    )
    await session.commit()


async def reset_data(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE appointments, vehicles, customers RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture(scope="session")
async def db_setup():
    admin = await asyncpg.connect(ADMIN_DSN)
    exists = await admin.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
    )
    if not exists:
        await admin.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    await admin.close()

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await seed_reference_data(session)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seed_ids(db_setup):
    engine = db_setup
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        dealership = await session.scalar(
            select(Dealership).where(Dealership.name == "Saigon Auto Service")
        )
        oil = await session.scalar(
            select(ServiceType).where(ServiceType.name == "Oil Change")
        )
        full = await session.scalar(
            select(ServiceType).where(ServiceType.name == "Full Service")
        )
        diagnostics = await session.scalar(
            select(ServiceType).where(ServiceType.name == "Engine Diagnostics")
        )
        return {
            "dealership_id": dealership.id,
            "oil_change_id": oil.id,
            "full_service_id": full.id,
            "diagnostics_id": diagnostics.id,
        }


@pytest_asyncio.fixture
async def client(db_setup):
    engine = db_setup
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    await reset_data(engine)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    await reset_data(engine)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session(db_setup):
    engine = db_setup
    maker = async_sessionmaker(engine, expire_on_commit=False)
    await reset_data(engine)
    async with maker() as session:
        yield session
    await reset_data(engine)
