"""Shared test fixtures and helpers for dcc-mcp-maya tests.

Provides:
- ``SKILLS_ROOT`` — Path to ``src/dcc_mcp_maya/skills/``
- ``load_skill_script(skill_dir, script_name)`` — load a skill script by path
- ``make_mock_maya(cmds_attrs, mel_attrs)`` — build a (mock_maya, mock_cmds, mock_mel) triple
- ``load_and_call(rel_path, mock_cmds, func_name, **kwargs)`` — load a skill script with
  maya mocked, call ``func_name`` (default ``"main"``) with ``**kwargs``, return result dict
- ``load_and_call_with_mel(rel_path, mock_cmds, mock_mel, func_name, **kwargs)`` — same as
  ``load_and_call`` but also patches ``maya.mel``
- ``mock_maya_modules`` — autouse fixture for server tests
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


def load_and_call(
    rel_path: str,
    mock_cmds: Any,
    func_name: str = "main",
    **kwargs: Any,
) -> dict:
    """Load a skill script with Maya mocked and call *func_name* with *kwargs*.

    Keeps the ``maya`` / ``maya.cmds`` mock active during **both** module load
    and function invocation, which prevents ``ImportError`` inside scripts that
    import ``maya.cmds`` at module level or inside the function body.

    Args:
        rel_path: Path relative to ``SKILLS_ROOT``, e.g.
            ``"maya-scene/scripts/get_scene_info.py"``.
        mock_cmds: A ``MagicMock`` configured to behave like ``maya.cmds``.
        func_name: Name of the callable to invoke (default ``"main"``).
        **kwargs: Keyword arguments forwarded to the called function.

    Returns:
        The result dict returned by the skill function.

    Example::

        result = load_and_call("maya-scene/scripts/create_object.py", mock_cmds, type="sphere")
        assert result["success"] is True
    """
    _MOD_COUNTER[0] += 1
    script_path = SKILLS_ROOT / rel_path
    module_name = "skill_lac_{}_{}".format(rel_path.replace("/", "_").replace(".", "_"), _MOD_COUNTER[0])

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    fake_modules = {
        "maya": mock_maya,
        "maya.cmds": mock_cmds,
        "maya.api": MagicMock(),
        "maya.api.OpenMaya": MagicMock(),
        "maya.utils": MagicMock(),
    }

    with patch.dict(sys.modules, fake_modules):
        spec = importlib.util.spec_from_file_location(module_name, str(script_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, func_name)
        return func(**kwargs)


def load_and_call_with_mel(
    rel_path: str,
    mock_cmds: Any,
    mock_mel: Optional[Any] = None,
    func_name: str = "main",
    **kwargs: Any,
) -> dict:
    """Like :func:`load_and_call` but also patches ``maya.mel``.

    Required for scripts that call ``maya.mel.eval(...)`` or
    ``import maya.mel as mel`` inside the function body.

    Args:
        rel_path: Path relative to ``SKILLS_ROOT``.
        mock_cmds: A ``MagicMock`` configured to behave like ``maya.cmds``.
        mock_mel: Optional ``MagicMock`` for ``maya.mel``.  A new one is
            created if *None* is passed.
        func_name: Name of the callable to invoke (default ``"main"``).
        **kwargs: Keyword arguments forwarded to the called function.

    Returns:
        The result dict returned by the skill function.
    """
    if mock_mel is None:
        mock_mel = MagicMock()

    _MOD_COUNTER[0] += 1
    script_path = SKILLS_ROOT / rel_path
    module_name = "skill_lacm_{}_{}".format(rel_path.replace("/", "_").replace(".", "_"), _MOD_COUNTER[0])

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_maya.mel = mock_mel

    fake_modules = {
        "maya": mock_maya,
        "maya.cmds": mock_cmds,
        "maya.mel": mock_mel,
        "maya.api": MagicMock(),
        "maya.api.OpenMaya": MagicMock(),
        "maya.utils": MagicMock(),
    }

    with patch.dict(sys.modules, fake_modules):
        spec = importlib.util.spec_from_file_location(module_name, str(script_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, func_name)
        return func(**kwargs)


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
