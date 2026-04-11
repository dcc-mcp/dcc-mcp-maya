"""Shared test fixtures and helpers for dcc-mcp-maya tests.

Provides:
- ``load_skill_script(skill_dir, script_name)`` — load a skill script by path
- ``make_mock_maya(cmds_attrs)`` — build a (mock_maya, mock_cmds) pair
- ``mock_maya_modules`` — autouse fixture for server tests
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from unittest.mock import MagicMock

# Import third-party modules
import pytest

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def load_skill_script(skill_dir: str, script_name: str):
    """Load a skill script module by path.

    Uses a unique module name per call to avoid module cache collisions
    when the same script is loaded multiple times in a test session.

    Args:
        skill_dir: Directory name under ``skills/`` (may contain hyphens).
        script_name: Script stem name (without ``.py`` extension).

    Returns:
        The loaded module object.
    """
    _MOD_COUNTER[0] += 1
    script_path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_{}_{}_{}" .format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_mock_maya(
    cmds_attrs: Optional[Dict] = None,
) -> Tuple[MagicMock, MagicMock]:
    """Return ``(mock_maya, mock_cmds)`` with the ``.cmds`` linkage wired.

    Args:
        cmds_attrs: Optional dict of attribute name → return value to set on
            ``mock_cmds`` (e.g. ``{"objExists": MagicMock(return_value=True)}``).

    Returns:
        Tuple of ``(mock_maya, mock_cmds)``.
    """
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mock_cmds, k, v)
    return mock_maya, mock_cmds
