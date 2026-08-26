from __future__ import annotations

from typing import Any


def as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def valid_choice(value: Any, choices: list[dict], key: str = "id") -> bool:
    return any(str(choice[key]) == str(value) for choice in choices)

