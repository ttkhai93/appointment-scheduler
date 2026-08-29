from datetime import UTC, date, datetime, time, timedelta, timezone

import pytest

from app.exceptions import DomainValidationError
from app.services.timeutil import (
    business_day_slots,
    ensure_utc,
    validate_grid,
)


def test_ensure_utc_aware():
    dt = datetime(2026, 9, 1, 8, 0, tzinfo=timezone(timedelta(hours=7)))
    assert ensure_utc(dt) == datetime(2026, 9, 1, 1, 0, tzinfo=UTC)


def test_ensure_utc_naive_assumed_utc():
    dt = datetime(2026, 9, 1, 1, 0)  # noqa: DTZ001 (intentionally naive input)
    assert ensure_utc(dt) == datetime(2026, 9, 1, 1, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "minute,second,microsecond", [(30, 0, 0), (0, 1, 0), (0, 0, 1)]
)
def test_validate_grid_rejects_off_grid(minute, second, microsecond):
    dt = datetime(2026, 9, 1, 9, minute, second, microsecond, tzinfo=UTC)
    with pytest.raises(DomainValidationError):
        validate_grid(dt, 60)


def test_business_day_slots_single_slot_duration():
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
