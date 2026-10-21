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

from dcc_mcp_maya.headless import serve_headless

stop_event = threading.Event()


def _handle_stop(_signum, _frame) -> None:
    stop_event.set()


def main() -> None:
    maya.standalone.initialize(name="python")

    gateway_raw = os.environ.get("DCC_MCP_GATEWAY_PORT", "0")
    gateway_port = int(gateway_raw) if gateway_raw and gateway_raw != "0" else None

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    def announce(server):
        print("[dcc-mcp-maya] standalone MCP:", server.mcp_url, flush=True)
        print("[dcc-mcp-maya] press Ctrl+C to stop", flush=True)

    try:
        serve_headless(gateway_port=gateway_port, stop_event=stop_event, on_started=announce)
    finally:
        maya.standalone.uninitialize()



if __name__ == "__main__":
    main()
