"""Tests for cooperative cancellation inside the ``maya-render-farm`` skill.

Covers the final outstanding bullet of issue #85: the example skill
(``maya-render-farm``) must use :func:`check_maya_cancelled` at safe
checkpoints inside its per-node loops so a long validation scan can be
aborted promptly instead of blocking the UI thread until the full scene
has been inspected.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dcc_mcp_core.cancellation import (
    CancelledError,
    CancelToken,
    reset_cancel_token,
    set_cancel_token,
)

SKILL_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "dcc_mcp_maya"
    / "skills"
    / "maya-render-farm"
    / "scripts"
    / "validate_scene_for_farm.py"
)


@pytest.fixture
def validate_module(monkeypatch):
    """Import ``validate_scene_for_farm.py`` with ``maya.cmds`` stubbed out.

    The skill script does ``import maya.cmds`` lazily inside the function
    body, so we install a mocked ``maya.cmds`` module in ``sys.modules``
    before the function runs.  Ten synthetic ``file`` nodes give the per-
    node cancellation checkpoint something to iterate over.
    """

    maya_cmds = MagicMock()
    # Scene is saved so the loop is actually reached.
    maya_cmds.file.return_value = "/tmp/fake.ma"
    # 10 file nodes — more than enough to test a mid-loop cancellation.
    maya_cmds.ls.return_value = [f"file{i}" for i in range(10)]
    maya_cmds.getAttr.return_value = "/nonexistent/tex.png"

    maya_pkg = MagicMock()
    maya_pkg.cmds = maya_cmds
    monkeypatch.setitem(sys.modules, "maya", maya_pkg)
    monkeypatch.setitem(sys.modules, "maya.cmds", maya_cmds)

    # Load the skill script as a standalone module.
    spec = importlib.util.spec_from_file_location("validate_scene_for_farm_under_test", SKILL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, maya_cmds


def test_validate_scene_for_farm_imports_check_maya_cancelled(validate_module):
    """Regression guard — the skill must keep using the public probe."""
    module, _ = validate_module
    source = SKILL_SCRIPT.read_text(encoding="utf-8")
    assert "from dcc_mcp_maya.dispatcher import check_maya_cancelled" in source
    # It must be called at least twice — once per loop (file nodes + refs).
    assert source.count("check_maya_cancelled()") >= 2
    # And the imported name is actually bound in the module namespace.
    assert hasattr(module, "check_maya_cancelled")


def test_validate_scene_for_farm_honours_cancellation_mid_scan(validate_module):
    """A cancel after the first file node must abort before the scan finishes.

    We install a core ``CancelToken``, cancel it from inside the first
    ``cmds.getAttr`` call, and assert:

    1. ``validate_scene_for_farm`` propagates ``CancelledError`` — it does
       **not** swallow the cancellation into ``skill_exception``.
    2. Only the first iteration touched ``getAttr``; the remaining nine
       nodes are skipped (cooperative cancellation semantics, not
       best-effort).
    """

    module, maya_cmds = validate_module

    token = CancelToken()
    reset = set_cancel_token(token)

    call_counter = {"get_attr": 0}

    def _getattr_then_cancel(_attr):
        call_counter["get_attr"] += 1
        if call_counter["get_attr"] == 1:
            # Simulate ``notifications/cancelled`` arriving just after the
            # first node's attribute has been fetched but before the next
            # loop iteration's ``check_maya_cancelled`` checkpoint fires.
            token.cancel()
        return "/nonexistent/tex.png"

    maya_cmds.getAttr.side_effect = _getattr_then_cancel

    try:
        with pytest.raises(CancelledError):
            module.validate_scene_for_farm()
    finally:
        reset_cancel_token(reset)

    # Only one node was inspected before the probe aborted the scan.
    assert call_counter["get_attr"] == 1
    # The reference loop should not have run at all.
    assert maya_cmds.referenceQuery.call_count == 0
