"""Maya minimal-mode configuration.

The actual progressive-loading implementation lives in ``dcc-mcp-core``.
This module only declares Maya's default eager skills and group policy so
``MayaMcpServer`` can pass a ``MinimalModeConfig`` to core.
"""

from __future__ import annotations

from typing import Iterable, Optional

from dcc_mcp_core import MinimalModeConfig

MINIMAL_SKILLS = ("maya-scripting", "maya-scene")
MINIMAL_DEACTIVATE_GROUPS = {
    "maya-scripting": ("extended",),
    "maya-scene": ("scene-management",),
}


def build_minimal_mode_config(skill_names: Optional[Iterable[str]] = None) -> MinimalModeConfig:
    """Build Maya's declarative minimal-mode config for core."""
    skills = tuple(skill_names) if skill_names is not None else MINIMAL_SKILLS
    return MinimalModeConfig(
        skills=skills,
        deactivate_groups=MINIMAL_DEACTIVATE_GROUPS,
    )
