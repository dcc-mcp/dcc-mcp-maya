"""Regression coverage for the bundled Maya GUI bootstrap."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def test_user_setup_uses_maya_lowest_priority_queue(monkeypatch) -> None:
    scheduled = []
    maya_module = ModuleType("maya")
    cmds_module = ModuleType("maya.cmds")

    def eval_deferred(callback, **kwargs):
        scheduled.append((callback, kwargs))

    cmds_module.evalDeferred = eval_deferred
    maya_module.cmds = cmds_module
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds_module)

    path = Path(__file__).resolve().parents[1] / "maya" / "userSetup.py"
    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_user_setup", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert len(scheduled) == 1
    callback, kwargs = scheduled[0]
    assert callback is module._load_dcc_mcp_maya
    assert kwargs == {"lowestPriority": True}
