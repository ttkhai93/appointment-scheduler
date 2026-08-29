from datetime import UTC, date, datetime, time, timedelta, timezone

import pytest

from app.exceptions import DomainValidationError
from app.services.timeutil import (
    business_day_slots,
    ensure_utc,
    validate_grid,
)


def test_ensure_utc_aware():
    """A timezone-aware datetime is normalized to UTC."""
    dt = datetime(2026, 9, 1, 8, 0, tzinfo=timezone(timedelta(hours=7)))
    assert ensure_utc(dt) == datetime(2026, 9, 1, 1, 0, tzinfo=UTC)


def test_ensure_utc_naive_assumed_utc():
    """A naive datetime is assumed to be UTC and made timezone-aware."""
    dt = datetime(2026, 9, 1, 1, 0)  # noqa: DTZ001 (intentionally naive input)
    assert ensure_utc(dt) == datetime(2026, 9, 1, 1, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "minute,second,microsecond", [(30, 0, 0), (0, 1, 0), (0, 0, 1)]
)
def test_validate_grid_rejects_off_grid(minute, second, microsecond):
    """Off-grid datetimes (misaligned minute, second, or microsecond) are rejected."""
    dt = datetime(2026, 9, 1, 9, minute, second, microsecond, tzinfo=UTC)
    with pytest.raises(DomainValidationError):
        validate_grid(dt, 60)


def test_validate_grid_accepts_on_grid():
    """A datetime aligned to the slot grid passes validation."""
    dt = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
    validate_grid(dt, 60)


def test_business_day_slots_single_slot_duration():
    """A 60-minute service over an 08:00-17:30 day yields nine hourly slots in UTC."""
    slots = business_day_slots(
        date(2026, 8, 31),  # Monday
        time(8, 0),
        time(17, 30),
        "Asia/Ho_Chi_Minh",
        duration_minutes=60,
        slot_minutes=60,
    )
    assert len(slots) == 9
    assert slots[0] == (
        datetime(2026, 8, 31, 1, 0, tzinfo=UTC),
        datetime(2026, 8, 31, 2, 0, tzinfo=UTC),
    )
    assert slots[-1] == (
        datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
        datetime(2026, 8, 31, 10, 0, tzinfo=UTC),
    )


def test_business_day_slots_two_hour_duration():
    """A 120-minute service over the same day yields eight start slots."""
    slots = business_day_slots(
        date(2026, 8, 31),
        time(8, 0),
        time(17, 30),
        "Asia/Ho_Chi_Minh",
        duration_minutes=120,
        slot_minutes=60,
    )
    assert len(slots) == 8
    assert slots[-1][1] == datetime(2026, 8, 31, 10, 0, tzinfo=UTC)


def test_unknown_timezone_rejected():
    """An unknown timezone name raises DomainValidationError."""
    with pytest.raises(DomainValidationError):
        business_day_slots(
            date(2026, 8, 31),
            time(8, 0),
            time(17, 30),
            "Not/AZone",
            duration_minutes=60,
            slot_minutes=60,
        )


def test_business_day_slots_empty_when_duration_exceeds_day():
    """A service longer than the open window produces no slots."""
    slots = business_day_slots(
        date(2026, 8, 31),
        time(8, 0),
        time(17, 30),
        "Asia/Ho_Chi_Minh",
        duration_minutes=600,
        slot_minutes=60,
    )
    assert slots == []
