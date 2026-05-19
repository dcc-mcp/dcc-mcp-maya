"""Regression coverage for MCP-scoped ``cmds.file`` prompt blocking."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from dcc_mcp_maya._cmds_file_guard import MayaFilePromptBlockedError, guard_cmds_file
from dcc_mcp_maya._executor import run_skill_script


class _FakeCmds:
    def __init__(self, *, modified: bool = False, scene_name: str = "c:/shot.ma") -> None:
        self.modified = modified
        self.scene_name = scene_name
        self.calls = []

    def file(self, *args, **kwargs):
        self.calls.append((args, dict(kwargs)))
        if kwargs.get("query") or kwargs.get("q"):
            if kwargs.get("modified") or kwargs.get("mf"):
                return self.modified
            if kwargs.get("sceneName") or kwargs.get("sn"):
                return self.scene_name
        if kwargs.get("new") and not kwargs.get("force"):
            raise AssertionError("modal save prompt would have opened")
        if kwargs.get("open") and not kwargs.get("force"):
            raise AssertionError("modal save prompt would have opened")
        if (kwargs.get("i") or kwargs.get("import")) and "prompt" not in kwargs:
            raise AssertionError("import prompt was not suppressed")
        return "ok"


@pytest.fixture
def fake_maya_modules(monkeypatch):
    maya_mod = types.ModuleType("maya")
    cmds = _FakeCmds()
    maya_mod.cmds = cmds
    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    return cmds


def test_guard_blocks_dirty_new_without_force(fake_maya_modules):
    fake_maya_modules.modified = True

    with guard_cmds_file(fake_maya_modules), pytest.raises(MayaFilePromptBlockedError):
        fake_maya_modules.file(new=True)

    assert fake_maya_modules.calls == [((), {"query": True, "modified": True})]


def test_guard_adds_force_when_new_scene_is_clean(fake_maya_modules):
    with guard_cmds_file(fake_maya_modules):
        assert fake_maya_modules.file(new=True) == "ok"

    assert fake_maya_modules.calls[-1] == ((), {"new": True, "force": True})


def test_guard_adds_prompt_false_for_imports(fake_maya_modules):
    with guard_cmds_file(fake_maya_modules):
        assert fake_maya_modules.file("c:/asset.fbx", i=True) == "ok"

    assert fake_maya_modules.calls[-1] == (("c:/asset.fbx",), {"i": True, "prompt": False})


def test_guard_restores_original_file_callable(fake_maya_modules):
    original_func = fake_maya_modules.file.__func__

    with guard_cmds_file(fake_maya_modules):
        assert getattr(fake_maya_modules.file, "_dcc_mcp_file_guard", False)

    assert fake_maya_modules.file.__func__ is original_func


def test_run_skill_script_wraps_cmds_file(tmp_path: Path, fake_maya_modules):
    fake_maya_modules.modified = True
    script = tmp_path / "dirty_new_scene.py"
    script.write_text(
        "def main(**kwargs):\n"
        "    import maya.cmds as cmds\n"
        "    cmds.file(new=True)\n"
        "    return {'success': True, 'message': 'unexpected'}\n",
        encoding="utf-8",
    )

    result = run_skill_script(str(script), {})

    assert result["success"] is False
    assert "force=True" in result["message"]
    assert fake_maya_modules.calls == [((), {"query": True, "modified": True})]
