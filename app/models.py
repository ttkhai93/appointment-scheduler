from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Dealership(Base):
    __tablename__ = "dealerships"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    address: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    technicians: Mapped[list[Technician]] = relationship(back_populates="dealership")
    service_bays: Mapped[list[ServiceBay]] = relationship(back_populates="dealership")


class ServiceType(Base):
    __tablename__ = "service_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer)

    technicians: Mapped[list[Technician]] = relationship(
        secondary="technician_qualifications", back_populates="qualifications"
    )


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    dealership_id: Mapped[int] = mapped_column(
        ForeignKey("dealerships.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120))

    dealership: Mapped[Dealership] = relationship(back_populates="technicians")
    qualifications: Mapped[list[ServiceType]] = relationship(
        secondary="technician_qualifications", back_populates="technicians"
    )


class TechnicianQualification(Base):
    __tablename__ = "technician_qualifications"

    technician_id: Mapped[int] = mapped_column(
        ForeignKey("technicians.id", ondelete="CASCADE"), primary_key=True
    )
    service_type_id: Mapped[int] = mapped_column(
        ForeignKey("service_types.id", ondelete="CASCADE"), primary_key=True
    )


class ServiceBay(Base):
    __tablename__ = "service_bays"

    id: Mapped[int] = mapped_column(primary_key=True)
    dealership_id: Mapped[int] = mapped_column(
        ForeignKey("dealerships.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(80))

    dealership: Mapped[Dealership] = relationship(back_populates="service_bays")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str] = mapped_column(String(32))
    full_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    year: Mapped[int | None] = mapped_column(Integer)
    vin: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        ExcludeConstraint(
            ("service_bay_id", "="),
            (text("tstzrange(start_time, end_time)"), "&&"),
            using="gist",
            name="uq_appointments_no_bay_overlap",
        ),
        ExcludeConstraint(
            ("technician_id", "="),
            (text("tstzrange(start_time, end_time)"), "&&"),
            using="gist",
            name="uq_appointments_no_tech_overlap",
        ),
        Index("ix_appointments_start_time", "start_time"),
        Index("ix_appointments_dealership_start", "dealership_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dealership_id: Mapped[int] = mapped_column(
        ForeignKey("dealerships.id", ondelete="CASCADE")
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE")
    )
    technician_id: Mapped[int] = mapped_column(
        ForeignKey("technicians.id", ondelete="CASCADE")
    )
    service_bay_id: Mapped[int] = mapped_column(
        ForeignKey("service_bays.id", ondelete="CASCADE")
    )
    service_type_id: Mapped[int] = mapped_column(
        ForeignKey("service_types.id", ondelete="CASCADE")
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer: Mapped[Customer] = relationship()
    vehicle: Mapped[Vehicle] = relationship()
    technician: Mapped[Technician] = relationship()
    service_bay: Mapped[ServiceBay] = relationship()
    service_type: Mapped[ServiceType] = relationship()
