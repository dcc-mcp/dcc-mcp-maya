"""Tests for Maya plug-in faulthandler setup."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


def test_plugin_faulthandler_writes_traceback_on_fatal_signal(tmp_path: Path) -> None:
    plugin_path = Path(__file__).parent.parent / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"
    script = textwrap.dedent(
        """
        import importlib.util
        import os
        import sys
        import types
        from unittest.mock import MagicMock

        maya = types.ModuleType("maya")
        maya.cmds = MagicMock()
        maya.api = types.ModuleType("maya.api")
        maya.api.OpenMaya = MagicMock()
        sys.modules["maya"] = maya
        sys.modules["maya.cmds"] = maya.cmds
        sys.modules["maya.api"] = maya.api
        sys.modules["maya.api.OpenMaya"] = maya.api.OpenMaya

        os.environ["DCC_MCP_LOG_DIR"] = r"{log_dir}"
        spec = importlib.util.spec_from_file_location("_plugin", r"{plugin_path}")
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)
        plugin._enable_faulthandler_for_plugin()

        import faulthandler
        faulthandler._sigsegv()
        """
    ).format(log_dir=str(tmp_path), plugin_path=str(plugin_path))

    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert proc.returncode != 0
    logs = list(tmp_path.glob("maya-faulthandler-*.log"))
    assert logs, "faulthandler should create a crash log in DCC_MCP_LOG_DIR"
    body = logs[0].read_text(errors="replace")
    assert "Fatal Python error" in body
    assert "Current thread" in body or "Thread" in body
