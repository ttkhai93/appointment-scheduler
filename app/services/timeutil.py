from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.exceptions import DomainValidationError


def ensure_utc(dt: datetime) -> datetime:
    """Normalize a datetime to UTC; naive datetimes are assumed to be UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def ensure_start_on_slot_boundary(dt: datetime, slot_minutes: int) -> None:
    """Ensure a start time lands exactly on a slot boundary (assumption A3)."""
    if dt.minute % slot_minutes != 0 or dt.second != 0 or dt.microsecond != 0:
        raise DomainValidationError(
            f"start_time must fall on the {slot_minutes}-minute grid"
        )


def get_zoneinfo(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise DomainValidationError(f"unknown timezone: {tz_name}") from exc


def business_day_slots(
    local_date: date,
    open_time: time,
    close_time: time,
    tz_name: str,
    duration_minutes: int,
    slot_minutes: int,
) -> list[tuple[datetime, datetime]]:
    """Build (start, end) UTC slot pairs within a dealership's business day.

    Slots start on the grid; a slot is only included if it fits entirely
    before close_time.
    """
    tz = get_zoneinfo(tz_name)
    open_dt = datetime.combine(local_date, open_time, tzinfo=tz)
    close_dt = datetime.combine(local_date, close_time, tzinfo=tz)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=slot_minutes)

    slots: list[tuple[datetime, datetime]] = []
    cursor = open_dt
    while cursor + duration <= close_dt:
        end = cursor + duration
        slots.append((cursor.astimezone(UTC), end.astimezone(UTC)))
        cursor = cursor + step
    return slots
