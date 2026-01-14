from __future__ import annotations

import re
from datetime import timedelta


DURATION_PATTERN = re.compile(r"(\d+)([hms])", re.IGNORECASE)
FRACTION_SPLIT_PATTERN = re.compile(r"\s*/\s*")

INVALID_DURATION_MESSAGE = (
    "Invalid duration. Use AhBmCs (e.g. 2h30m) or HH:MM:SS. "
    "You can also use remaining/total like 3h/5h."
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


def parse_duration(duration_str: str):
    """Parse duration; support remaining/total with a slash or a single duration.

    Returns (remaining_seconds, total_seconds).
    """
    duration_str = duration_str.strip()
    if not duration_str:
        raise ValueError(INVALID_DURATION_MESSAGE)

    fraction_parts = FRACTION_SPLIT_PATTERN.split(duration_str, maxsplit=1)
    if len(fraction_parts) == 2:
        remaining_raw, total_raw = fraction_parts
        try:
            rh, rm, rs = _parse_single_duration(remaining_raw)
            th, tm, ts = _parse_single_duration(total_raw)
        except ValueError:
            raise ValueError(INVALID_DURATION_MESSAGE)

        remaining_sec = duration_to_seconds(rh, rm, rs)
        total_sec = duration_to_seconds(th, tm, ts)

        if remaining_sec <= 0 or total_sec <= 0:
            raise ValueError(
                "Duration must be positive (parsed as remaining/total like 3h/5h)."
            )
        if remaining_sec > total_sec:
            raise ValueError(
                "Remaining duration cannot exceed total duration "
                "(parsed as remaining/total like 3h/5h)."
            )

        return remaining_sec, total_sec

    try:
        h, m, s = _parse_single_duration(duration_str)
    except ValueError:
        raise ValueError(INVALID_DURATION_MESSAGE)
    single_sec = duration_to_seconds(h, m, s)
    return single_sec, single_sec
