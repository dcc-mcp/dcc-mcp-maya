"""E2E tests for ``_commandport.suppress_security_warnings`` (issue #148).

These exercise the helper against a real Maya standalone interpreter so we
catch any drift in the ``commandPort -q -name`` / ``cmds.commandPort``
contract across Maya versions (2022, 2023, 2024, 2025).

Note: ``mayapy`` is headless, so the actual modal "Allow / Deny / Allow All"
dialog does not render here. The test focuses on the helper's interaction
with the live Maya API:

* It must successfully detect an open port via ``commandPort -q -name``.
* It must close+reopen each port without raising.
* The port must remain listenable after the helper completes.

Run::

    mayapy -m pytest tests/e2e/test_commandport_e2e.py -v
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import socket

# Import third-party modules
import pytest

maya_standalone = pytest.importorskip(
    "maya.standalone",
    reason="maya.standalone not available — run under mayapy",
)

try:
    maya_standalone.initialize(name="python")
except Exception:
    pass

# Import local modules
from dcc_mcp_maya import _commandport  # noqa: E402
from maya import cmds  # noqa: E402

pytestmark = pytest.mark.e2e


def _free_tcp_port() -> int:
    """Return a likely-free TCP port on the loopback interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _close_port_silent(name: str) -> None:
    try:
        cmds.commandPort(name=name, close=True)
    except Exception:
        pass


class TestSuppressSecurityWarningsE2E:
    def test_no_open_ports_returns_zero(self, monkeypatch):
        """No commandPorts open ⇒ helper is a no-op."""
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        # Make sure we start clean (best-effort; ports we did not open are left alone).
        assert _commandport.suppress_security_warnings() >= 0

    def test_env_opt_out_short_circuits(self, monkeypatch):
        """``DCC_MCP_MAYA_DISABLE_COMMANDPORT_WARNING=0`` ⇒ helper returns 0
        without touching any port."""
        port_name = ":{}".format(_free_tcp_port())
        cmds.commandPort(name=port_name, sourceType="mel", securityWarning=True)
        try:
            monkeypatch.setenv(_commandport.ENV_DISABLE_WARNING, "0")
            assert _commandport.suppress_security_warnings() == 0
            # The port we opened with sw=True must still be listed.
            listed = cmds.commandPort(name=port_name, q=True, exists=True)
            assert listed is True
        finally:
            _close_port_silent(port_name)

    def test_reopens_existing_port_with_sw_disabled(self, monkeypatch):
        """When a commandPort is open, helper closes+reopens it and counts it."""
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        port_name = ":{}".format(_free_tcp_port())
        cmds.commandPort(name=port_name, sourceType="mel", securityWarning=True)
        try:
            ports_before = _commandport._list_open_ports()
            assert port_name in ports_before, ports_before
            fixed = _commandport.suppress_security_warnings()
            assert fixed >= 1
            # Port must still exist after the close/reopen cycle.
            assert cmds.commandPort(name=port_name, q=True, exists=True) is True
        finally:
            _close_port_silent(port_name)

    def test_helper_is_idempotent(self, monkeypatch):
        """Running the helper twice does not raise and the port stays alive."""
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        port_name = ":{}".format(_free_tcp_port())
        cmds.commandPort(name=port_name, sourceType="mel", securityWarning=True)
        try:
            _commandport.suppress_security_warnings()
            _commandport.suppress_security_warnings()
            assert cmds.commandPort(name=port_name, q=True, exists=True) is True
        finally:
            _close_port_silent(port_name)

    def test_list_open_ports_includes_explicit_port(self, monkeypatch):
        """``_list_open_ports`` correctly enumerates a port we just opened."""
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        port_name = ":{}".format(_free_tcp_port())
        cmds.commandPort(name=port_name, sourceType="mel", securityWarning=False)
        try:
            ports = _commandport._list_open_ports()
            assert port_name in ports
        finally:
            _close_port_silent(port_name)
