"""Unit tests for ``examples/multi-instance/userSetup.py``.

These tests exercise the import-safe helpers without launching Maya.  The
goal is to make sure the example does not rot: if we rename an env var or
change the default port range, these tests fail first.
"""

from __future__ import annotations

import importlib.util
import os
import socket
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


def test_default_port_range_is_reserved_block(user_setup):
    """The example ships with a fixed, documented port block."""
    assert list(user_setup.PORT_RANGE) == list(range(8765, 8776))
    assert user_setup.DEFAULT_GATEWAY_PORT == 9765


def test_pick_free_port_returns_available_port(user_setup):
    """``pick_free_port`` must hand out a currently-bindable port."""
    port = user_setup.pick_free_port(user_setup.PORT_RANGE)
    # Either a port from the range, or the 0-fallback when everything is busy.
    assert port == 0 or port in user_setup.PORT_RANGE


def test_pick_free_port_skips_busy_port(user_setup):
    """When the first candidate is taken, the second is chosen."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        try:
            busy.bind(("127.0.0.1", 0))
        except OSError:
            pytest.skip("cannot bind an ephemeral port on this host")
        taken_port = busy.getsockname()[1]
        # Feed a two-element candidate list: [taken, free-in-range]
        free_candidate = next(
            (p for p in user_setup.PORT_RANGE if p != taken_port and user_setup._port_is_free(p)),
            None,
        )
        if free_candidate is None:
            pytest.skip("reserved multi-instance port range is busy on this host")
        chosen = user_setup.pick_free_port([taken_port, free_candidate])
        assert chosen == free_candidate


def test_apply_multi_instance_env_sets_expected_keys(user_setup, monkeypatch):
    """``apply_multi_instance_env`` populates the three env vars from #88."""
    for key in ("DCC_MCP_MAYA_PORT", "DCC_MCP_GATEWAY_PORT", "DCC_MCP_MAYA_DCC_PID"):
        monkeypatch.delenv(key, raising=False)

    user_setup.apply_multi_instance_env(dcc_pid=424242)

    assert os.environ["DCC_MCP_MAYA_DCC_PID"] == "424242"
    assert os.environ["DCC_MCP_GATEWAY_PORT"] == str(user_setup.DEFAULT_GATEWAY_PORT)
    # Port must be numeric and either 0 or in the reserved range.
    port = int(os.environ["DCC_MCP_MAYA_PORT"])
    assert port == 0 or port in user_setup.PORT_RANGE


def test_apply_multi_instance_env_preserves_operator_overrides(user_setup, monkeypatch):
    """An operator-set ``DCC_MCP_GATEWAY_PORT`` must not be clobbered."""
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "9999")
    monkeypatch.setenv("DCC_MCP_MAYA_DCC_PID", "12345")
    monkeypatch.delenv("DCC_MCP_MAYA_PORT", raising=False)

    user_setup.apply_multi_instance_env()

    assert os.environ["DCC_MCP_GATEWAY_PORT"] == "9999"
    assert os.environ["DCC_MCP_MAYA_DCC_PID"] == "12345"
    # Port is always re-computed — env should contain a fresh value.
    assert "DCC_MCP_MAYA_PORT" in os.environ
