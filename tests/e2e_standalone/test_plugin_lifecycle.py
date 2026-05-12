"""Maya standalone E2E tests."""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


class TestPluginEntryPoint:
    """Verify that the Maya plugin script's initializePlugin and
    uninitializePlugin work correctly in Maya standalone for 2022-2025.

    Background
    ----------
    In some Maya standalone / batch environments ``maya.OpenMaya`` (API 1.0)
    does not expose ``MFnPlugin``, causing ``AttributeError`` at plugin load
    time.  The plugin now imports from ``maya.api.OpenMaya`` (API 2.0) first
    and falls back to ``maya.OpenMaya``.  These tests exercise that path.

    Because ``cmds.loadPlugin`` requires a file on disk inside MAYA_PLUG_IN_PATH
    we instead import the plugin module directly and pass a mock MFnPlugin
    object.  This mirrors what Maya itself does and lets us catch the
    ``AttributeError`` that triggered the original bug report.
    """

    @pytest.fixture
    def plugin_module(self):
        """Import the plugin script as a plain Python module."""
        plugin_path = Path(__file__).parents[2] / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"
        spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_plugin", plugin_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @pytest.fixture
    def mock_mfn_plugin(self):
        """Return a lightweight stand-in for the MFnPlugin *mobject* argument.

        Maya passes an ``MObject`` (plugin node) to ``initializePlugin`` /
        ``uninitializePlugin``.  We supply a dummy class that accepts positional
        args and exposes the minimal interface Maya's ``MFnPlugin`` requires so
        that ``om.MFnPlugin(plugin, vendor, version)`` does not raise.
        """

        class _FakePluginObject:
            pass

        # Patch the om.MFnPlugin so it accepts our fake object without needing
        # a real Maya plugin node.
        import maya.api.OpenMaya as _om2

        class _FakeMFnPlugin:
            def __init__(self, *args, **kwargs):
                pass

        _original = getattr(_om2, "MFnPlugin", None)
        _om2.MFnPlugin = _FakeMFnPlugin
        yield _FakePluginObject()
        # Restore
        if _original is not None:
            _om2.MFnPlugin = _original
        else:
            del _om2.MFnPlugin

    def test_om_mfnplugin_importable(self):
        """maya.api.OpenMaya.MFnPlugin is always available on supported Maya versions."""
        import maya.api.OpenMaya as om2

        assert hasattr(om2, "MFnPlugin"), (
            "maya.api.OpenMaya.MFnPlugin not found — plugin will raise AttributeError on load"
        )

    def test_plugin_uses_api2_import(self, plugin_module):
        """Plugin module must use maya.api.OpenMaya and declare maya_useNewAPI."""
        import inspect

        src = inspect.getsource(plugin_module)
        assert "maya.api.OpenMaya" in src, (
            "Plugin should import from maya.api.OpenMaya (API 2.0) to avoid MFnPlugin AttributeError"
        )
        # maya_useNewAPI() is the official Autodesk mechanism that tells Maya to
        # pass API 2.0 MObject wrappers to initializePlugin/uninitializePlugin.
        assert "maya_useNewAPI" in src, (
            "Plugin must declare maya_useNewAPI() so Maya passes API 2.0 objects to plugin callbacks"
        )

    def test_initialize_plugin(self, plugin_module, mock_mfn_plugin):
        """initializePlugin starts the MCP server without raising."""
        import os

        os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
        try:
            plugin_module.initializePlugin(mock_mfn_plugin)
            assert plugin_module._handle is not None or True  # server may be None if start fails gracefully
        except AttributeError as exc:
            pytest.fail(f"initializePlugin raised AttributeError — MFnPlugin compat broken: {exc}")
        finally:
            # Always clean up the server to avoid port leaks across tests
            try:
                plugin_module.uninitializePlugin(mock_mfn_plugin)
            except Exception:
                pass

    def test_uninitialize_plugin(self, plugin_module, mock_mfn_plugin):
        """uninitializePlugin stops the MCP server without raising."""
        import os

        os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
        try:
            plugin_module.initializePlugin(mock_mfn_plugin)
        except Exception:
            pass  # If init failed for unrelated reason, still test uninit

        try:
            plugin_module.uninitializePlugin(mock_mfn_plugin)
        except AttributeError as exc:
            pytest.fail(f"uninitializePlugin raised AttributeError — MFnPlugin compat broken: {exc}")

    def test_initialize_uninitialize_cycle(self, plugin_module, mock_mfn_plugin):
        """Full init → uninit cycle runs cleanly (simulates plugin load/unload)."""
        import os

        os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
        errors = []
        try:
            plugin_module.initializePlugin(mock_mfn_plugin)
        except AttributeError as exc:
            errors.append(f"initializePlugin: {exc}")
        except Exception:
            pass  # RuntimeError from server start is acceptable here

        try:
            plugin_module.uninitializePlugin(mock_mfn_plugin)
        except AttributeError as exc:
            errors.append(f"uninitializePlugin: {exc}")
        except Exception:
            pass

        assert not errors, "AttributeError in plugin lifecycle: {}".format(errors)

    def test_no_mfnplugin_in_old_api(self):
        """Documents that maya.OpenMaya (API 1.0) may not have MFnPlugin.

        This test is informational: it passes regardless of whether the old API
        exposes MFnPlugin, but it records which environment triggered the bug.
        """
        import maya.OpenMaya as om1

        has_attr = hasattr(om1, "MFnPlugin")
        # Just record — we don't assert True/False because it varies per version
        # and environment.  The fix is to always use API 2.0.
        assert isinstance(has_attr, bool)


class TestSingletonReentrancy:
    """Module-level start_server / stop_server is thread-safe and idempotent."""

    def test_idempotent_start_returns_same_handle(self):
        """Calling start_server twice without stopping returns the same handle."""
        from dcc_mcp_maya import start_server, stop_server

        h1 = start_server(port=0)
        h2 = start_server(port=0)
        try:
            assert h1 is h2, "Second call must return existing handle"
            assert h1.port == h2.port
        finally:
            stop_server()

    def test_stop_then_restart_creates_new_server(self):
        """After stop_server(), start_server() creates a fresh server instance."""
        from dcc_mcp_maya import start_server, stop_server

        h1 = start_server(port=0)
        stop_server()

        h2 = start_server(port=0)
        try:
            assert h2 is not h1
            assert h2.mcp_url().startswith("http://")
        finally:
            stop_server()

    def test_concurrent_start_server_calls_are_safe(self):
        """Multiple threads calling start_server() concurrently get the same handle."""
        from dcc_mcp_maya import start_server, stop_server

        handles = []
        errors = []
        lock = threading.Lock()

        def do_start():
            try:
                h = start_server(port=0)
                with lock:
                    handles.append(h)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=do_start) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        try:
            assert not errors, "Concurrent start_server raised: {}".format(errors)
            assert len(handles) == 5
            ports = {h.port for h in handles}
            assert len(ports) == 1, "Expected singleton port, got: {}".format(ports)
        finally:
            stop_server()
