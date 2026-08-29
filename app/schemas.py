from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=3, max_length=32)


class VehicleCreate(BaseModel):
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int | None = Field(default=None, ge=1900, le=2100)
    vin: str | None = Field(default=None, max_length=32)


class AppointmentCreate(BaseModel):
    dealership_id: int
    service_type_id: int
    # Aware datetime recommended; naive datetimes are treated as UTC
    # (assumption A5: all storage is UTC).
    start_time: datetime
    customer: CustomerCreate
    vehicle: VehicleCreate


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    make: str
    model: str
    year: int | None
    vin: str | None


class TechnicianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealership_id: int
    name: str
    # Populated by the catalog endpoint; empty for nested appointment payloads.
    qualification_ids: list[int] = Field(default_factory=list)


class ServiceBayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealership_id: int
    name: str


class ServiceTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    duration_minutes: int


class DealershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    timezone: str


class BusinessHoursOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealership_id: int
    # Python weekday(): 0 = Monday ... 6 = Sunday.
    day_of_week: int
    open_time: time
    close_time: time


class TechnicianQualificationOut(BaseModel):
    technician_id: int
    technician_name: str
    service_type_id: int
    service_type_name: str


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealership_id: int
    service_type_id: int
    status: str
    start_time: datetime
    end_time: datetime
    created_at: datetime
    customer: CustomerOut
    vehicle: VehicleOut
    technician: TechnicianOut
    service_bay: ServiceBayOut
    service_type: ServiceTypeOut


class AvailabilitySlot(BaseModel):
    start_time: datetime
    end_time: datetime


class AvailabilityResponse(BaseModel):
    date: date
    service_type_id: int
    slots: list[AvailabilitySlot]


class AvailabilityCheckResponse(BaseModel):
    available: bool
    reason: str | None = None
