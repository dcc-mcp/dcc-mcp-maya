"""Unit tests for ``examples/multi-instance/userSetup.py``.

These tests exercise the import-safe helpers without launching Maya.  The
goal is to make sure the example does not rot: if we rename an env var or
change the default port range, these tests fail first.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "multi-instance" / "userSetup.py"


@pytest.fixture(scope="module")
def user_setup():
    """Import ``examples/multi-instance/userSetup.py`` as a module."""
    spec = importlib.util.spec_from_file_location("_mi_user_setup_example", EXAMPLE)
    assert spec and spec.loader, f"failed to build spec for {EXAMPLE}"
    module = importlib.util.module_from_spec(spec)
    saved_maya = sys.modules.get("maya")
    saved_maya_utils = sys.modules.get("maya.utils")
    sys.modules[spec.name] = module
    sys.modules["maya"] = None
    sys.modules["maya.utils"] = None
    try:
        spec.loader.exec_module(module)
    finally:
        if saved_maya is None:
            sys.modules.pop("maya", None)
        else:
            sys.modules["maya"] = saved_maya
        if saved_maya_utils is None:
            sys.modules.pop("maya.utils", None)
        else:
            sys.modules["maya.utils"] = saved_maya_utils
    try:
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def test_gateway_port_remains_stable(user_setup):
    assert user_setup.DEFAULT_GATEWAY_PORT == 9765


def test_apply_multi_instance_env_sets_expected_keys(user_setup, monkeypatch):
    """``apply_multi_instance_env`` populates the three env vars from #88."""
    for key in ("DCC_MCP_MAYA_PORT", "DCC_MCP_GATEWAY_PORT", "DCC_MCP_MAYA_DCC_PID"):
        monkeypatch.delenv(key, raising=False)

    user_setup.apply_multi_instance_env(dcc_pid=424242)

    assert os.environ["DCC_MCP_MAYA_DCC_PID"] == "424242"
    assert os.environ["DCC_MCP_GATEWAY_PORT"] == str(user_setup.DEFAULT_GATEWAY_PORT)
    assert "DCC_MCP_MAYA_PORT" not in os.environ


def test_apply_multi_instance_env_preserves_operator_overrides(user_setup, monkeypatch):
    """An operator-set ``DCC_MCP_GATEWAY_PORT`` must not be clobbered."""
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "9999")
    monkeypatch.setenv("DCC_MCP_MAYA_DCC_PID", "12345")
    monkeypatch.setenv("DCC_MCP_MAYA_PORT", "19001")

    user_setup.apply_multi_instance_env()

    assert os.environ["DCC_MCP_GATEWAY_PORT"] == "9999"
    assert os.environ["DCC_MCP_MAYA_DCC_PID"] == "12345"
    assert os.environ["DCC_MCP_MAYA_PORT"] == "19001"
