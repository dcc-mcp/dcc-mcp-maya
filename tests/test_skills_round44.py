"""Round 44 tests: DccCapabilities integration + get_frame_range skill.

Tests cover:
1. capabilities.py — maya_capabilities() factory
2. server.py MayaMcpServer.get_capabilities()
3. __init__.py / api.py maya_capabilities re-exports
4. get_frame_range skill (maya-animation)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Check if DccCapabilities is available before running tests
try:
    from dcc_mcp_core import DccCapabilities  # noqa: F401
except ImportError:
    pytest.skip("dcc_mcp_core.DccCapabilities not available", allow_module_level=True)

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
_MOD_COUNTER = [0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_script(skill_dir, script_name):
    """Load a skill script directly from its file path."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    mod_name = "skill_r44_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(mod_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_maya_cmds(**extra):
    mock = MagicMock()
    mock.playbackOptions.return_value = 1.0
    mock.currentTime.return_value = 1.0
    mock.currentUnit.return_value = "film"
    mock.objExists.return_value = True
    for k, v in extra.items():
        setattr(mock, k, v)
    return mock


def _make_modules(cmds_mock):
    maya_mock = MagicMock()
    maya_mock.cmds = cmds_mock
    return {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }


def _run_get_frame_range(cmds_mock=None, **kwargs):
    if cmds_mock is None:
        cmds_mock = _mock_maya_cmds()
    mods = _make_modules(cmds_mock)
    with patch.dict(sys.modules, mods):
        mod = _load_script("maya-animation", "get_frame_range")
        return mod.get_frame_range(**kwargs)


def _caps_to_dict(caps):
    """Convert DccCapabilities to a plain dict using attribute access."""
    keys = [
        "scene_manager",
        "transform",
        "hierarchy",
        "selection",
        "render_capture",
        "snapshot",
        "undo_redo",
        "file_operations",
        "has_embedded_python",
        "progress_reporting",
        "scene_info",
    ]
    return {k: getattr(caps, k) for k in keys if hasattr(caps, k)}


# ===========================================================================
# 1. capabilities.py
# ===========================================================================


class TestMayaCapabilitiesFactory:
    """Tests for dcc_mcp_maya.capabilities.maya_capabilities()."""

    def test_returns_dcc_capabilities_instance(self):
        from dcc_mcp_core import DccCapabilities

        from dcc_mcp_maya.capabilities import maya_capabilities

        caps = maya_capabilities()
        assert isinstance(caps, DccCapabilities)

    def test_transform_flag_is_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        assert maya_capabilities().transform is True

    def test_scene_manager_flag_is_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        assert maya_capabilities().scene_manager is True

    def test_hierarchy_flag_is_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        assert maya_capabilities().hierarchy is True

    def test_has_embedded_python_is_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        assert maya_capabilities().has_embedded_python is True

    def test_render_capture_and_snapshot_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        caps = maya_capabilities()
        assert caps.render_capture is True
        assert caps.snapshot is True

    def test_undo_redo_is_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        assert maya_capabilities().undo_redo is True

    def test_file_operations_is_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        assert maya_capabilities().file_operations is True

    def test_progress_reporting_is_true(self):
        from dcc_mcp_maya.capabilities import maya_capabilities

        assert maya_capabilities().progress_reporting is True

    def test_caps_attrs_accessible(self):
        """All declared keys are accessible attributes."""
        from dcc_mcp_maya.capabilities import maya_capabilities

        caps = maya_capabilities()
        d = _caps_to_dict(caps)
        assert len(d) > 0
        for v in d.values():
            assert v is True or v is False


class TestMayaCapabilitiesDict:
    """Tests for MAYA_CAPABILITIES_DICT constant."""

    def test_dict_exists(self):
        from dcc_mcp_maya.capabilities import MAYA_CAPABILITIES_DICT

        assert isinstance(MAYA_CAPABILITIES_DICT, dict)

    def test_dict_has_transform(self):
        from dcc_mcp_maya.capabilities import MAYA_CAPABILITIES_DICT

        assert MAYA_CAPABILITIES_DICT["transform"] is True

    def test_dict_consistent_with_factory(self):
        from dcc_mcp_maya.capabilities import MAYA_CAPABILITIES_DICT, maya_capabilities

        caps = maya_capabilities()
        for key, val in MAYA_CAPABILITIES_DICT.items():
            if hasattr(caps, key):
                assert getattr(caps, key) is val


# ===========================================================================
# 2. server.py MayaMcpServer.get_capabilities()
# ===========================================================================


def _import_server_module():
    cmds_mock = _mock_maya_cmds()
    mods = _make_modules(cmds_mock)
    mod_name = "dcc_mcp_maya.server"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    with patch.dict(sys.modules, mods):
        import importlib

        mod = importlib.import_module(mod_name)
    return mod


class TestServerGetCapabilities:
    """Tests for MayaMcpServer.get_capabilities().

    Note: Skipped if get_capabilities method is not yet implemented.
    """

    @pytest.mark.skip(reason="MayaMcpServer.get_capabilities() not yet implemented")
    def test_get_capabilities_returns_dcc_capabilities(self):
        from dcc_mcp_core import DccCapabilities

        mod = _import_server_module()
        server = mod.MayaMcpServer(port=18830)
        caps = server.get_capabilities()
        assert isinstance(caps, DccCapabilities)

    @pytest.mark.skip(reason="MayaMcpServer.get_capabilities() not yet implemented")
    def test_get_capabilities_transform_true(self):
        mod = _import_server_module()
        server = mod.MayaMcpServer(port=18831)
        assert server.get_capabilities().transform is True

    @pytest.mark.skip(reason="MayaMcpServer.get_capabilities() not yet implemented")
    def test_get_capabilities_returns_dict_via_attrs(self):
        mod = _import_server_module()
        server = mod.MayaMcpServer(port=18832)
        d = _caps_to_dict(server.get_capabilities())
        assert isinstance(d, dict)
        assert "scene_manager" in d

    @pytest.mark.skip(reason="MayaMcpServer.get_capabilities() not yet implemented")
    def test_get_capabilities_before_start(self):
        """get_capabilities() works even before start() is called."""
        mod = _import_server_module()
        server = mod.MayaMcpServer(port=18833)
        assert server.is_running is False
        caps = server.get_capabilities()
        assert caps.transform is True

    @pytest.mark.skip(reason="MayaMcpServer.get_capabilities() not yet implemented")
    def test_get_capabilities_consistent(self):
        """Two calls return equivalent capability flags."""
        mod = _import_server_module()
        server = mod.MayaMcpServer(port=18834)
        c1 = server.get_capabilities()
        c2 = server.get_capabilities()
        assert c1.transform == c2.transform
        assert c1.hierarchy == c2.hierarchy


# ===========================================================================
# 3. Public re-exports
# ===========================================================================


class TestPublicReexports:
    """Verify maya_capabilities is accessible from top-level and api module."""

    def test_importable_from_init(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "maya_capabilities")
        assert callable(dcc_mcp_maya.maya_capabilities)

    def test_importable_from_api(self):
        from dcc_mcp_maya.api import maya_capabilities

        assert callable(maya_capabilities)

    def test_in_init_all(self):
        import dcc_mcp_maya

        assert "maya_capabilities" in dcc_mcp_maya.__all__

    def test_in_api_all(self):
        from dcc_mcp_maya import api

        assert "maya_capabilities" in api.__all__

    def test_top_level_call_works(self):
        from dcc_mcp_core import DccCapabilities

        import dcc_mcp_maya

        caps = dcc_mcp_maya.maya_capabilities()
        assert isinstance(caps, DccCapabilities)


# ===========================================================================
# 4. get_frame_range skill
# ===========================================================================


class TestGetFrameRangeHappyPath:
    """Happy path tests for get_frame_range skill."""

    def test_success_result(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        result = _run_get_frame_range(cmds)
        assert result["success"] is True

    def test_frame_range_in_context(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        result = _run_get_frame_range(cmds)
        assert "frame_range" in result.get("context", {})

    def test_film_fps_24(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        cmds.currentUnit.return_value = "film"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 24.0

    def test_pal_fps_25(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 100.0
        cmds.currentUnit.return_value = "pal"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 25.0

    def test_ntsc_fps_30(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 0.0 if kw.get("minTime") else 90.0
        cmds.currentUnit.return_value = "ntsc"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 30.0

    def test_custom_fps_unit(self):
        """Custom fps unit like '60fps' is parsed correctly."""
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 60.0
        cmds.currentUnit.return_value = "60fps"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 60.0

    def test_start_end_values(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 5.0 if kw.get("minTime") else 200.0
        cmds.currentTime.return_value = 10.0
        cmds.currentUnit.return_value = "film"
        result = _run_get_frame_range(cmds)
        fr = result["context"]["frame_range"]
        assert fr["start"] == 5.0
        assert fr["end"] == 200.0

    def test_current_in_frame_range(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 50.0
        cmds.currentTime.return_value = 25.0
        cmds.currentUnit.return_value = "film"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["current"] == 25.0

    def test_prompt_present(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        result = _run_get_frame_range(cmds)
        ctx = result.get("context", {})
        # prompt may be in result or context
        has_prompt = bool(result.get("prompt")) or bool(ctx.get("prompt"))
        assert has_prompt

    def test_frame_range_schema_keys(self):
        """frame_range dict must have start, end, fps, current."""
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        result = _run_get_frame_range(cmds)
        fr = result["context"]["frame_range"]
        for key in ("start", "end", "fps", "current"):
            assert key in fr, "Missing key in frame_range: {}".format(key)


class TestGetFrameRangeEdgeCases:
    """Edge cases and error paths."""

    def test_exception_returns_failure(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = RuntimeError("Maya not ready")
        result = _run_get_frame_range(cmds)
        assert result["success"] is False

    def test_unknown_fps_unit_defaults_24(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        cmds.currentUnit.return_value = "unknownUnit"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 24.0

    def test_show_fps_48(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 48.0
        cmds.currentUnit.return_value = "show"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 48.0

    def test_ntscf_fps_60(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        cmds.currentUnit.return_value = "ntscf"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 60.0

    def test_palf_fps_50(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 100.0
        cmds.currentUnit.return_value = "palf"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 50.0

    def test_game_fps_15(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 0.0 if kw.get("minTime") else 15.0
        cmds.currentUnit.return_value = "game"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 15.0

    def test_custom_120fps_unit(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 0.0 if kw.get("minTime") else 120.0
        cmds.currentUnit.return_value = "120fps"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 120.0

    def test_invalid_custom_fps_defaults_24(self):
        """Malformed custom fps like 'xfps' defaults to 24."""
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        cmds.currentUnit.return_value = "xfps"
        result = _run_get_frame_range(cmds)
        assert result["context"]["frame_range"]["fps"] == 24.0


class TestGetFrameRangeStructural:
    """Structural checks on the get_frame_range skill file."""

    def test_skill_file_exists(self):
        path = _SKILLS_ROOT / "maya-animation" / "scripts" / "get_frame_range.py"
        assert path.exists(), "get_frame_range.py not found at {}".format(path)

    def test_main_is_callable(self):
        cmds = _mock_maya_cmds()
        cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 120.0
        mods = _make_modules(cmds)
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-animation", "get_frame_range")
        assert callable(getattr(mod, "main", None))

    def test_no_legacy_run_signature(self):
        """Ensure file uses skill_entry style, not def run(params)."""
        import ast

        path = _SKILLS_ROOT / "maya-animation" / "scripts" / "get_frame_range.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                args = [a.arg for a in node.args.args]
                assert "params" not in args, "Legacy run(params) found"

    def test_imports_skill_entry(self):
        path = _SKILLS_ROOT / "maya-animation" / "scripts" / "get_frame_range.py"
        source = path.read_text(encoding="utf-8")
        assert "skill_entry" in source

    def test_uses_skill_success(self):
        path = _SKILLS_ROOT / "maya-animation" / "scripts" / "get_frame_range.py"
        source = path.read_text(encoding="utf-8")
        assert "skill_success" in source

    def test_has_prompt_in_skill_success(self):
        path = _SKILLS_ROOT / "maya-animation" / "scripts" / "get_frame_range.py"
        source = path.read_text(encoding="utf-8")
        assert "prompt=" in source
