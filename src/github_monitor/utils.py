"""Utility functions for github-monitor."""

import re
from datetime import timedelta


def parse_duration_to_timedelta(duration_str: str) -> timedelta:
    """Parse duration string like '5m', '1h30m', '2d' to timedelta.

    Args:
        duration_str: Duration string

    Returns:
        timedelta object
    """
    if not duration_str:
        return timedelta(seconds=5)

    total_seconds = 0
    # Pattern matches: number followed by unit (d, h, m, s)
    pattern = r"(\d+)([dhms])"
    matches = re.findall(pattern, duration_str.lower())

    if not matches:
        return timedelta(seconds=5)

    for value, unit in matches:
        value = int(value)
        if unit == "d":
            total_seconds += value * 86400
        elif unit == "h":
            total_seconds += value * 3600
        elif unit == "m":
            total_seconds += value * 60
        elif unit == "s":
            total_seconds += value

    return timedelta(seconds=total_seconds if total_seconds > 0 else 5)
