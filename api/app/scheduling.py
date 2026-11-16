from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Use a valid IANA timezone, such as Asia/Kolkata") from exc


def next_occurrence(schedule_time: time, timezone_name: str, now: datetime | None = None) -> datetime:
    zone = validate_timezone(timezone_name)
    now_utc = (now or datetime.now(UTC)).astimezone(UTC)
    local_now = now_utc.astimezone(zone)
    start_day: date = local_now.date()
    requested = schedule_time.replace(tzinfo=None)

    # Skip a nonexistent wall time on a daylight-saving transition. On an
    # ambiguous fall-back time, fold=0 schedules one occurrence, not two.
    for offset in range(0, 9):
        naive = datetime.combine(start_day + timedelta(days=offset), requested)
        candidate = naive.replace(tzinfo=zone, fold=0)
        round_trip = candidate.astimezone(UTC).astimezone(zone)
        if round_trip.replace(tzinfo=None) != naive:
            continue
        if candidate.astimezone(UTC) > now_utc:
            return candidate.astimezone(UTC)
    raise ValueError("Could not calculate the next daily run")
