"""Bootstrap dcc-mcp-maya with the core HostAdapter runtime."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
import signal
import threading
from typing import Any, Dict, Optional

# Import local modules
from dcc_mcp_maya._plugin_dispatcher import (
    install_plugin_host_startup,
    resolve_plugin_host_startup,
)
from dcc_mcp_maya.server import start_server, stop_server

_STOP = threading.Event()


def _maya_is_background() -> bool:
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        return bool(cmds.about(batch=True))
    except ImportError:
        return True


def _server_kwargs() -> Dict[str, Any]:
    gateway_raw = os.environ.get("DCC_MCP_GATEWAY_PORT", "0")
    try:
        gateway_port: Optional[int] = int(gateway_raw)
    except ValueError:
        gateway_port = None
    if gateway_port is not None and gateway_port <= 0:
        gateway_port = None
    return {
        "gateway_port": gateway_port,
        "registry_dir": os.environ.get("DCC_MCP_REGISTRY_DIR") or None,
    }


def _install_signal_handlers() -> None:
    def _stop(_signum: int, _frame: object) -> None:
        _STOP.set()
        stop_server()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)


def main() -> Any:
    """Start the Maya MCP server and drive its host dispatcher."""
    is_background = _maya_is_background()
    startup = resolve_plugin_host_startup(is_background)
    install_plugin_host_startup(startup)
    handle = start_server(host_dispatcher=startup.dispatcher, **_server_kwargs())
    _install_signal_handlers()
    if startup.host is not None:
        if is_background:
            try:
                startup.host.run_headless(stop_event=_STOP)
            finally:
                stop_server()
        else:
            startup.host.start()
        return handle

    if is_background:
        try:
            _STOP.wait()
        finally:
            stop_server()
    return handle


if __name__ == "__main__":
    main()
