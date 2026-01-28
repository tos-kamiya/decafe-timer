from __future__ import annotations

import re
from datetime import timedelta


DURATION_PATTERN = re.compile(r"(\d+)([hms])", re.IGNORECASE)
INVALID_DURATION_MESSAGE = (
    "Invalid duration. Use AhBmCs (e.g. 2h30m) or HH:MM:SS."
)
INVALID_INTAKE_DURATION_MESSAGE = (
    "Invalid duration. Use AhBmCs (e.g. 2h30m) or HH:MM:SS."
)


def _parse_single_duration(duration_str: str):
    """Parse duration from HH:MM:SS or AhBmCs style into (h, m, s)."""
    duration_str = duration_str.strip()
    if not duration_str:
        raise ValueError

    if ":" in duration_str:
        parts = duration_str.split(":")
        if len(parts) != 3:
            raise ValueError
        try:
            h, m, s = map(int, parts)
        except ValueError as exc:
            raise ValueError from exc
        if any(value < 0 for value in (h, m, s)):
            raise ValueError
        if h == m == s == 0:
            raise ValueError
        return h, m, s

    normalized = duration_str.replace(" ", "").lower()
    if not normalized:
        raise ValueError

    pos = 0
    hours = minutes = seconds = 0
    for match in DURATION_PATTERN.finditer(normalized):
        if match.start() != pos:
            raise ValueError
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit == "h":
            hours += value
        elif unit == "m":
            minutes += value
        elif unit == "s":
            seconds += value
        pos = match.end()

    if pos != len(normalized):
        raise ValueError

    if hours == minutes == seconds == 0:
        raise ValueError

    return hours, minutes, seconds


def duration_to_seconds(hours: int, minutes: int, seconds: int) -> int:
    return int(timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds())


def parse_simple_duration(duration_str: str) -> int:
    """Parse a single duration (no remaining/total). Returns seconds."""
    duration_str = duration_str.strip()
    if not duration_str:
        raise ValueError(INVALID_INTAKE_DURATION_MESSAGE)
    try:
        h, m, s = _parse_single_duration(duration_str)
    except ValueError:
        raise ValueError(INVALID_INTAKE_DURATION_MESSAGE)
    return duration_to_seconds(h, m, s)
