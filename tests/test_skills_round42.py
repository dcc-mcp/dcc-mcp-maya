"""Round 42 tests — maya_warning for Arnold fallback paths.

Tests:
- create_hdri_dome: Arnold fallback emits maya_warning (mtoa not loaded)
- create_hdri_dome: Arnold success path returns skill_success (no warning)
- create_hdri_dome: structural checks (import maya_warning, call in else branch)
- create_render_pass: Arnold renderer + mtoa not loaded → maya_warning fallback
- create_render_pass: Arnold renderer + mtoa loaded → skill_success (aiAOV)
- create_render_pass: mayaSoftware renderer → skill_success (renderPass)
- create_render_pass: structural checks (import maya_warning, call in fallback)
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_maya_mock(mtoa_loaded: bool = False):
    """Return (mock_maya, mock_cmds) with pluginInfo configured."""
    mock_cmds = MagicMock()
    mock_cmds.pluginInfo.return_value = mtoa_loaded
    mock_cmds.createNode.side_effect = lambda node_type, **kw: kw.get("name", node_type + "1")
    mock_cmds.setAttr.return_value = None
    mock_cmds.connectAttr.return_value = None
    mock_cmds.attributeQuery.return_value = True
    mock_cmds.ls.return_value = []

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    return mock_maya, mock_cmds


def _load_create_hdri_dome(mtoa_loaded: bool):
    """Import create_hdri_dome with Maya mocked, return (module, cmds_mock)."""
    mock_maya, mock_cmds = _make_maya_mock(mtoa_loaded)

    # Use file path import to avoid hyphenated package name issues
    import importlib.util
    import os

    skill_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "dcc_mcp_maya",
        "skills",
        "maya-light-rig",
        "scripts",
        "create_hdri_dome.py",
    )
    spec = importlib.util.spec_from_file_location("create_hdri_dome", skill_path)
    mod = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
        spec.loader.exec_module(mod)

    return mod, mock_cmds


def _load_create_render_pass(mtoa_loaded: bool):
    """Import create_render_pass with Maya mocked."""
    mock_maya, mock_cmds = _make_maya_mock(mtoa_loaded)

    import importlib.util
    import os

    skill_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "dcc_mcp_maya",
        "skills",
        "maya-render-passes",
        "scripts",
        "create_render_pass.py",
    )
    spec = importlib.util.spec_from_file_location("create_render_pass", skill_path)
    mod = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
        spec.loader.exec_module(mod)

    return mod, mock_cmds


# ---------------------------------------------------------------------------
# Tests: create_hdri_dome
# ---------------------------------------------------------------------------

class TestCreateHdriDomeArnoldFallback:
    """create_hdri_dome — Arnold (mtoa) not loaded → ambientLight fallback + warning."""

    def _call(self, **kwargs):
        mock_maya, mock_cmds = _make_maya_mock(mtoa_loaded=False)
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            import importlib.util
            import os

            skill_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-light-rig",
                "scripts",
                "create_hdri_dome.py",
            )
            spec = importlib.util.spec_from_file_location("_dome_fallback", skill_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.create_hdri_dome(**kwargs), mock_cmds

    def test_fallback_returns_success_true(self):
        result, _ = self._call(hdri_path="/scene/sky.hdr")
        assert result["success"] is True

    def test_fallback_has_warning_key(self):
        result, _ = self._call(hdri_path="/scene/sky.hdr")
        assert "warning" in result.get("context", result)

    def test_fallback_warning_mentions_arnold(self):
        result, _ = self._call(hdri_path="/scene/sky.hdr")
        ctx = result.get("context", result)
        warning_val = ctx.get("warning", "")
        assert "arnold" in warning_val.lower() or "mtoa" in warning_val.lower()

    def test_fallback_has_dome_node(self):
        result, _ = self._call(hdri_path="/scene/sky.hdr")
        ctx = result.get("context", result)
        assert "dome_node" in ctx

    def test_fallback_has_prompt(self):
        result, _ = self._call(hdri_path="/scene/sky.hdr")
        assert result.get("prompt")

    def test_fallback_creates_ambient_light(self):
        """ambientLight node type must be used in fallback (not aiSkyDomeLight)."""
        _, mock_cmds = self._call(hdri_path="/sky.hdr")
        create_calls = [str(c) for c in mock_cmds.createNode.call_args_list]
        assert any("ambientLight" in c for c in create_calls)
        assert not any("aiSkyDomeLight" in c for c in create_calls)


class TestCreateHdriDomeArnoldSuccess:
    """create_hdri_dome — Arnold (mtoa) loaded → aiSkyDomeLight, no warning."""

    def _call(self, **kwargs):
        mock_maya, mock_cmds = _make_maya_mock(mtoa_loaded=True)
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            import importlib.util
            import os

            skill_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-light-rig",
                "scripts",
                "create_hdri_dome.py",
            )
            spec = importlib.util.spec_from_file_location("_dome_arnold", skill_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.create_hdri_dome(**kwargs), mock_cmds

    def test_arnold_success_returns_success_true(self):
        result, _ = self._call(hdri_path="/sky.hdr")
        assert result["success"] is True

    def test_arnold_success_no_warning_key(self):
        result, _ = self._call(hdri_path="/sky.hdr")
        ctx = result.get("context", result)
        assert not ctx.get("warning")

    def test_arnold_success_creates_aiSkyDomeLight(self):
        _, mock_cmds = self._call(hdri_path="/sky.hdr")
        create_calls = [str(c) for c in mock_cmds.createNode.call_args_list]
        assert any("aiSkyDomeLight" in c for c in create_calls)


class TestCreateHdriDomeStructural:
    """Structural checks on create_hdri_dome.py source."""

    def _source(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-light-rig",
            "scripts",
            "create_hdri_dome.py",
        )
        return open(path, encoding="utf-8").read()

    def test_imports_maya_warning(self):
        assert "from dcc_mcp_maya.api import maya_warning" in self._source()

    def test_calls_maya_warning(self):
        assert "maya_warning(" in self._source()

    def test_has_ambientLight_fallback(self):
        assert "ambientLight" in self._source()


# ---------------------------------------------------------------------------
# Tests: create_render_pass
# ---------------------------------------------------------------------------

class TestCreateRenderPassArnoldFallback:
    """create_render_pass — renderer=arnold but mtoa not loaded → renderPass + warning."""

    def _call(self, **kwargs):
        mock_maya, mock_cmds = _make_maya_mock(mtoa_loaded=False)
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            import importlib.util
            import os

            skill_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-render-passes",
                "scripts",
                "create_render_pass.py",
            )
            spec = importlib.util.spec_from_file_location("_rp_fallback", skill_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.create_render_pass(**kwargs), mock_cmds

    def test_fallback_success_true(self):
        result, _ = self._call(pass_type="beauty", renderer="arnold")
        assert result["success"] is True

    def test_fallback_has_warning(self):
        result, _ = self._call(pass_type="beauty", renderer="arnold")
        ctx = result.get("context", result)
        assert "warning" in ctx

    def test_fallback_warning_mentions_arnold(self):
        result, _ = self._call(pass_type="beauty", renderer="arnold")
        ctx = result.get("context", result)
        w = ctx.get("warning", "")
        assert "arnold" in w.lower() or "mtoa" in w.lower()

    def test_fallback_creates_renderpass_not_aiaov(self):
        _, mock_cmds = self._call(pass_type="diffuse", renderer="arnold")
        create_calls = [str(c) for c in mock_cmds.createNode.call_args_list]
        assert any("renderPass" in c for c in create_calls)
        assert not any("aiAOV" in c for c in create_calls)

    def test_fallback_renderer_in_context_is_mayaSoftware(self):
        result, _ = self._call(pass_type="beauty", renderer="arnold")
        ctx = result.get("context", result)
        assert ctx.get("renderer") == "mayaSoftware"

    def test_fallback_has_prompt(self):
        result, _ = self._call(pass_type="shadow", renderer="arnold")
        assert result.get("prompt")


class TestCreateRenderPassArnoldSuccess:
    """create_render_pass — renderer=arnold + mtoa loaded → aiAOV, no warning."""

    def _call(self, **kwargs):
        mock_maya, mock_cmds = _make_maya_mock(mtoa_loaded=True)
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            import importlib.util
            import os

            skill_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-render-passes",
                "scripts",
                "create_render_pass.py",
            )
            spec = importlib.util.spec_from_file_location("_rp_arnold", skill_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.create_render_pass(**kwargs), mock_cmds

    def test_arnold_success_true(self):
        result, _ = self._call(pass_type="beauty", renderer="arnold")
        assert result["success"] is True

    def test_arnold_no_warning(self):
        result, _ = self._call(pass_type="beauty", renderer="arnold")
        ctx = result.get("context", result)
        assert not ctx.get("warning")

    def test_arnold_creates_aiaov(self):
        _, mock_cmds = self._call(pass_type="diffuse", renderer="arnold")
        create_calls = [str(c) for c in mock_cmds.createNode.call_args_list]
        assert any("aiAOV" in c for c in create_calls)


class TestCreateRenderPassMayaSoftware:
    """create_render_pass — renderer=mayaSoftware → renderPass, no warning."""

    def _call(self, **kwargs):
        mock_maya, mock_cmds = _make_maya_mock(mtoa_loaded=False)
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            import importlib.util
            import os

            skill_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-render-passes",
                "scripts",
                "create_render_pass.py",
            )
            spec = importlib.util.spec_from_file_location("_rp_sw", skill_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.create_render_pass(**kwargs), mock_cmds

    def test_sw_success_true(self):
        result, _ = self._call(pass_type="beauty", renderer="mayaSoftware")
        assert result["success"] is True

    def test_sw_no_warning(self):
        result, _ = self._call(pass_type="beauty", renderer="mayaSoftware")
        ctx = result.get("context", result)
        assert not ctx.get("warning")

    def test_sw_creates_renderpass(self):
        _, mock_cmds = self._call(pass_type="shadow", renderer="mayaSoftware")
        create_calls = [str(c) for c in mock_cmds.createNode.call_args_list]
        assert any("renderPass" in c for c in create_calls)


class TestCreateRenderPassStructural:
    """Structural checks on create_render_pass.py source."""

    def _source(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-render-passes",
            "scripts",
            "create_render_pass.py",
        )
        return open(path, encoding="utf-8").read()

    def test_imports_maya_warning(self):
        assert "from dcc_mcp_maya.api import maya_warning" in self._source()

    def test_calls_maya_warning(self):
        assert "maya_warning(" in self._source()

    def test_checks_mtoa_plugin(self):
        assert 'pluginInfo("mtoa"' in self._source()
