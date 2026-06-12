"""Identity normalization helpers shared by plugin and sidecar launch code."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID


def normalize_instance_id(value: Optional[Any]) -> Optional[str]:
    """Return a canonical UUID string, or ``None`` when no valid id exists."""

    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return str(UUID(text))
    except (TypeError, ValueError):
        return None
