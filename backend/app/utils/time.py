from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Coerce a possibly-naive datetime to aware UTC (DB reads can be naive)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def captured_relative(dt: datetime, now: datetime | None = None) -> str:
    """Human 'time ago' string the server computes (the client can't reliably)."""
    now = now or utcnow()
    delta = now - as_utc(dt)
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    days = secs // 86400
    if days < 7:
        return f"{days}d ago"
    return as_utc(dt).strftime("%b %-d")


def day_label(dt: datetime, now: datetime | None = None) -> str:
    """'Today' / 'Yesterday' / 'Sun, Apr 19' grouping key."""
    now = now or utcnow()
    d = as_utc(dt).date()
    today = as_utc(now).date()
    delta = (today - d).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    return as_utc(dt).strftime("%a, %b %-d")


def meal_period(dt: datetime) -> str:
    """Derive meal period from the captured hour (UTC)."""
    h = as_utc(dt).hour
    if h < 11:
        return "breakfast"
    if h < 15:
        return "lunch"
    if h < 18:
        return "snack"
    return "dinner"
