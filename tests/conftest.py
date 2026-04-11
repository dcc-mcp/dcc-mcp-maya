"""Shared test fixtures and helpers for dcc-mcp-maya tests.

Provides:
- ``load_skill_script(skill_dir, script_name)`` — load a skill script by path
- ``make_mock_maya(cmds_attrs, mel_attrs)`` — build a (mock_maya, mock_cmds, mock_mel) triple
- ``mock_maya_modules`` — autouse fixture for server tests
- ``load_and_call(rel_path, mock_cmds, func_name, **kwargs)`` — load + call with mock active
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock, patch

# Import third-party modules

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
    module_name = "skill_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_mock_maya(
    cmds_attrs: Optional[Dict] = None,
    mel_attrs: Optional[Dict] = None,
) -> Tuple[MagicMock, MagicMock, MagicMock]:
    """Return ``(mock_maya, mock_cmds, mock_mel)`` with ``.cmds`` and ``.mel`` wired.

    Args:
        cmds_attrs: Optional dict of attribute name → return value to set on
            ``mock_cmds`` (e.g. ``{"objExists": MagicMock(return_value=True)}``).
        mel_attrs: Optional dict of attribute name → return value to set on
            ``mock_mel``.

    Returns:
        Tuple of ``(mock_maya, mock_cmds, mock_mel)``.
    """
    mock_cmds = MagicMock()
    mock_mel = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_maya.mel = mock_mel
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mock_cmds, k, v)
    if mel_attrs:
        for k, v in mel_attrs.items():
            setattr(mock_mel, k, v)
    return mock_maya, mock_cmds, mock_mel


_LOAD_COUNTER = [0]


def load_and_call(rel_path: str, mock_cmds: MagicMock, func_name: str = "main", **kwargs) -> Any:
    """Load a skill script and call a function with the Maya mock active throughout.

    This helper ensures the ``maya`` / ``maya.cmds`` mock is patched both during
    module *loading* and function *execution*, which is required for scripts that
    do ``import maya.cmds as cmds`` at the top level of the function body.

    Args:
        rel_path: Path relative to the ``skills/`` root, e.g.
            ``"maya-scene/scripts/create_object.py"``.
        mock_cmds: The :class:`~unittest.mock.MagicMock` to use as ``maya.cmds``.
        func_name: Name of the callable to invoke (default: ``"main"``).
        **kwargs: Keyword arguments forwarded to the callable.

    Returns:
        Whatever the skill function returns (typically an ActionResultModel dict).
    """
    _LOAD_COUNTER[0] += 1
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    fpath = SKILLS_ROOT / rel_path
    mod_name = "skill_lac_{}_{}".format(fpath.stem, _LOAD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(mod_name, str(fpath))
    mod = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
        spec.loader.exec_module(mod)
        fn = getattr(mod, func_name)
        return fn(**kwargs)
