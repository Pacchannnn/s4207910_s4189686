from __future__ import annotations

from typing import Any


def parse_int(
    value: str | None, default: int, label: str
) -> tuple[int, str | None]:
    if value is None or not value.strip():
        return default, None
    try:
        return int(value), None
    except (TypeError, ValueError):
        return default, f"{label} must be a whole number."


def valid_scalar(value: str, allowed: set[str]) -> bool:
    return value in allowed


def valid_choice(value: Any, choices: list[dict], key: str = "id") -> bool:
    return any(str(choice[key]) == str(value) for choice in choices)
