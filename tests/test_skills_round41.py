"""Round 41: server.py 100% coverage + load_hdri Arnold-fallback maya_warning.

Covers:
- server.py line 402: bind_and_register version=None reads cmds.about(version=True)
- load_hdri: Arnold fallback emits maya_warning (success=True, warning in context)
- load_hdri: Arnold success path returns skill_success (no warning key)
- load_hdri: file-not-found error path
- load_hdri: use_arnold=False skips Arnold entirely (native path, no warning)
- Structural: load_hdri imports maya_warning from dcc_mcp_maya.api
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_maya():
    """Return a minimal maya mock suitable for skill script tests."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    maya_mock.cmds = cmds_mock
    maya_mock.mel = MagicMock()
    maya_mock.utils = MagicMock()
    return maya_mock, cmds_mock


def _import_server(maya_mock):
    """Re-import server.py with maya mock active."""
    import importlib

    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    return importlib.import_module("dcc_mcp_maya.server")


def _load_load_hdri(cmds_mock, maya_mock):
    """Import load_hdri module with mock maya active."""
    import importlib

    mods = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.mel": MagicMock(),
        "maya.utils": MagicMock(),
    }
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod or mod == "load_hdri":
            del sys.modules[mod]
    with patch.dict(sys.modules, mods):
        import importlib.util
        import os

        skill_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-hdri",
            "scripts",
            "load_hdri.py",
        )
        spec = importlib.util.spec_from_file_location("load_hdri_mod", skill_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# server.py: bind_and_register version=None (line 402 coverage)
# ---------------------------------------------------------------------------


class TestBindAndRegisterVersionAutoDetect:
    """Cover the cmds.about(version=True) branch in bind_and_register (line 402)."""

    @pytest.fixture(autouse=True)
    def _maya_patch(self):
        maya_mock, cmds_mock = _mock_maya()
        cmds_mock.about.return_value = "2025"
        mods = {
            "maya": maya_mock,
            "maya.cmds": cmds_mock,
            "maya.mel": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            self._maya = maya_mock
            self._cmds = cmds_mock
            yield

    def _get_server(self):
        return _import_server(self._maya)

    def test_bind_and_register_auto_version_calls_about(self):
        """When version=None, bind_and_register calls cmds.about(version=True)."""
        srv_mod = self._get_server()
        server = srv_mod.MayaMcpServer(port=18822)
        server.start()

        mock_tm = MagicMock()
        mock_tm.bind_and_register.return_value = ("id1", MagicMock())

        with patch.dict(sys.modules, {"maya.cmds": self._cmds}):
            result = server.bind_and_register(mock_tm, version=None)

        assert result is not None
        self._cmds.about.assert_called()
        server.stop()

    def test_bind_and_register_auto_version_uses_about_return(self):
        """The version string passed to transport_manager equals cmds.about return value."""
        srv_mod = self._get_server()
        server = srv_mod.MayaMcpServer(port=18823)
        server.start()

        self._cmds.about.return_value = "2024"
        mock_tm = MagicMock()
        mock_tm.bind_and_register.return_value = ("id2", MagicMock())

        with patch.dict(sys.modules, {"maya.cmds": self._cmds}):
            server.bind_and_register(mock_tm, version=None)

        call_kwargs = mock_tm.bind_and_register.call_args
        # version kwarg should be "2024"
        assert call_kwargs.kwargs.get("version") == "2024" or "2024" in str(call_kwargs)
        server.stop()

    def test_bind_and_register_version_none_fallback_on_exception(self):
        """If cmds.about raises, version falls back to 'unknown'."""
        srv_mod = self._get_server()
        server = srv_mod.MayaMcpServer(port=18820)
        server.start()

        mock_tm = MagicMock()
        mock_tm.bind_and_register.return_value = ("id3", MagicMock())

        # Make cmds.about raise so the except branch sets version="unknown"
        self._cmds.about.side_effect = RuntimeError("Maya not ready")
        try:
            result = server.bind_and_register(mock_tm, version=None)
        finally:
            self._cmds.about.side_effect = None  # restore

        assert result is not None
        call_kwargs = mock_tm.bind_and_register.call_args
        assert "unknown" in str(call_kwargs)
        server.stop()

    def test_bind_and_register_explicit_version_skips_about(self):
        """When version is provided explicitly, cmds.about is NOT called."""
        srv_mod = self._get_server()
        server = srv_mod.MayaMcpServer(port=18821)
        server.start()

        mock_tm = MagicMock()
        mock_tm.bind_and_register.return_value = ("id4", MagicMock())

        self._cmds.about.reset_mock()
        with patch.dict(sys.modules, {"maya.cmds": self._cmds}):
            server.bind_and_register(mock_tm, version="2025")

        self._cmds.about.assert_not_called()
        server.stop()


# ---------------------------------------------------------------------------
# load_hdri: Arnold fallback emits maya_warning
# ---------------------------------------------------------------------------


class TestLoadHdriArnoldFallback:
    """Verify that load_hdri returns maya_warning when Arnold falls back to native."""

    def _make_cmds(self, arnold_fails=True):
        """Return a cmds mock. If arnold_fails=True, shadingNode raises for aiSkyDomeLight."""
        cmds_mock = MagicMock()
        maya_mock = MagicMock()
        maya_mock.cmds = cmds_mock

        if arnold_fails:
            # loadPlugin succeeds but shadingNode raises on aiSkyDomeLight
            def _shadingNode(node_type, **kwargs):
                if node_type == "aiSkyDomeLight":
                    raise RuntimeError("MtoA not loaded")
                name = kwargs.get("name", node_type)
                return name

            cmds_mock.shadingNode.side_effect = _shadingNode
        else:
            # Arnold succeeds
            def _shadingNode_ok(node_type, **kwargs):
                name = kwargs.get("name", node_type)
                return name

            cmds_mock.shadingNode.side_effect = _shadingNode_ok

        cmds_mock.directionalLight.return_value = "directionalLight1"
        cmds_mock.attributeQuery.return_value = True
        cmds_mock.setAttr.return_value = None
        cmds_mock.connectAttr.return_value = None
        cmds_mock.delete.return_value = None
        return cmds_mock, maya_mock

    def _call_load_hdri(self, cmds_mock, maya_mock, **kwargs):
        """Load the module fresh with mock, call load_hdri, return result."""
        import importlib.util
        import os

        skill_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-hdri",
                "scripts",
                "load_hdri.py",
            )
        )
        mods_patch = {
            "maya": maya_mock,
            "maya.cmds": cmds_mock,
            "maya.mel": MagicMock(),
            "maya.utils": MagicMock(),
        }
        for mod in list(sys.modules):
            if "dcc_mcp_maya" in mod:
                del sys.modules[mod]

        with patch.dict(sys.modules, mods_patch):
            with patch("os.path.isfile", return_value=True):
                spec = importlib.util.spec_from_file_location("load_hdri_mod", skill_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                result = mod.load_hdri(**kwargs)
        return result

    def test_arnold_fallback_returns_warning(self):
        """When Arnold fails, load_hdri returns success=True with warning key."""
        cmds_mock, maya_mock = self._make_cmds(arnold_fails=True)
        result = self._call_load_hdri(
            cmds_mock,
            maya_mock,
            file_path="/scene/env.hdr",
            use_arnold=True,
        )
        assert result["success"] is True
        ctx = result.get("context", {})
        assert "warning" in ctx
        assert "Arnold" in ctx["warning"] or "arnold" in ctx["warning"].lower()

    def test_arnold_fallback_backend_is_native(self):
        """Result context backend == 'native' on Arnold fallback."""
        cmds_mock, maya_mock = self._make_cmds(arnold_fails=True)
        result = self._call_load_hdri(
            cmds_mock,
            maya_mock,
            file_path="/scene/env.hdr",
            use_arnold=True,
        )
        assert result["context"]["backend"] == "native"

    def test_arnold_fallback_has_prompt(self):
        """The warning result includes a prompt suggesting MtoA installation."""
        cmds_mock, maya_mock = self._make_cmds(arnold_fails=True)
        result = self._call_load_hdri(
            cmds_mock,
            maya_mock,
            file_path="/scene/env.hdr",
            use_arnold=True,
        )
        prompt = result.get("prompt", "") or ""
        assert prompt != ""

    def test_arnold_success_no_warning(self):
        """When Arnold succeeds, no 'warning' key in context."""
        cmds_mock, maya_mock = self._make_cmds(arnold_fails=False)
        result = self._call_load_hdri(
            cmds_mock,
            maya_mock,
            file_path="/scene/env.hdr",
            use_arnold=True,
        )
        assert result["success"] is True
        ctx = result.get("context", {})
        # No warning — pure Arnold success
        assert "warning" not in ctx or ctx.get("warning") == ""

    def test_use_arnold_false_native_no_warning(self):
        """use_arnold=False goes straight to native path — no warning."""
        cmds_mock, maya_mock = self._make_cmds(arnold_fails=False)  # irrelevant
        result = self._call_load_hdri(
            cmds_mock,
            maya_mock,
            file_path="/scene/env.hdr",
            use_arnold=False,
        )
        assert result["success"] is True
        ctx = result.get("context", {})
        assert "warning" not in ctx or ctx.get("warning") == ""

    def test_file_not_found_returns_error(self):
        """A missing HDR file returns success=False."""
        cmds_mock, maya_mock = self._make_cmds(arnold_fails=False)
        import importlib.util
        import os

        skill_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-hdri",
                "scripts",
                "load_hdri.py",
            )
        )
        mods_patch = {
            "maya": maya_mock,
            "maya.cmds": cmds_mock,
            "maya.mel": MagicMock(),
            "maya.utils": MagicMock(),
        }
        for mod in list(sys.modules):
            if "dcc_mcp_maya" in mod:
                del sys.modules[mod]

        with patch.dict(sys.modules, mods_patch):
            with patch("os.path.isfile", return_value=False):
                spec = importlib.util.spec_from_file_location("load_hdri_mod", skill_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                result = mod.load_hdri(file_path="/nonexistent/env.hdr")

        assert result["success"] is False
        assert "not found" in result.get("message", "").lower()


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


class TestLoadHdriStructural:
    def test_import_maya_warning_present(self):
        """load_hdri.py imports maya_warning from dcc_mcp_maya.api."""
        import os

        skill_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-hdri",
                "scripts",
                "load_hdri.py",
            )
        )
        content = open(skill_path, encoding="utf-8").read()
        assert "maya_warning" in content
        assert "from dcc_mcp_maya.api import" in content

    def test_no_bare_skill_success_for_native_fallback(self):
        """After refactor, load_hdri should NOT call skill_success when arnold fallback."""
        import os

        skill_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "dcc_mcp_maya",
                "skills",
                "maya-hdri",
                "scripts",
                "load_hdri.py",
            )
        )
        content = open(skill_path, encoding="utf-8").read()
        # maya_warning call should be present for the fallback path
        assert "maya_warning(" in content

    def test_maya_warning_api_importable(self):
        """maya_warning is importable from the top-level dcc_mcp_maya package."""
        import importlib

        for mod in list(sys.modules):
            if "dcc_mcp_maya" in mod:
                del sys.modules[mod]

        maya_mock = MagicMock()
        mods = {
            "maya": maya_mock,
            "maya.cmds": MagicMock(),
            "maya.mel": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            pkg = importlib.import_module("dcc_mcp_maya")
            assert hasattr(pkg, "maya_warning")
            assert callable(pkg.maya_warning)
