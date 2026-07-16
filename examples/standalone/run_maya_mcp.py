"""Run dcc-mcp-maya from mayapy / maya.standalone.

Usage:
    mayapy examples/standalone/run_maya_mcp.py

Environment:
    DCC_MCP_MAYA_PORT=<optional fixed instance port>
    DCC_MCP_GATEWAY_PORT=0
    DCC_MCP_MAYA_SKILL_PATHS=/path/to/custom-skills
"""

from __future__ import annotations

import os
import signal
import threading

import maya.standalone

from dcc_mcp_maya import start_server, stop_server
from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

stop_event = threading.Event()


def _handle_stop(_signum, _frame) -> None:
    stop_event.set()
    stop_server()


def main() -> None:
    maya.standalone.initialize(name="python")

    gateway_raw = os.environ.get("DCC_MCP_GATEWAY_PORT", "0")
    gateway_port = int(gateway_raw) if gateway_raw and gateway_raw != "0" else None

    dispatcher = MayaStandaloneDispatcher()
    handle = start_server(
        gateway_port=gateway_port,
        host_dispatcher=dispatcher,
    )

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    print("[dcc-mcp-maya] standalone MCP:", handle.mcp_url())
    print("[dcc-mcp-maya] press Ctrl+C to stop")
    stop_event.wait()


if __name__ == "__main__":
    main()
