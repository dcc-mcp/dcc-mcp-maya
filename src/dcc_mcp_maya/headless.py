"""Foreground Mayapy serving through Core's owning-thread dispatcher."""

from __future__ import annotations

import threading
from typing import Callable, List, Optional

from dcc_mcp_core import __version__ as core_version
from dcc_mcp_core.host import BlockingDispatcher
from packaging.version import Version

from dcc_mcp_maya.host import MayaHost
from dcc_mcp_maya.server import MayaMcpServer


def serve_headless(
    *,
    port: Optional[int] = None,
    gateway_port: Optional[int] = None,
    registry_dir: Optional[str] = None,
    extra_skill_paths: Optional[List[str]] = None,
    stop_event: Optional[threading.Event] = None,
    on_started: Optional[Callable[[MayaMcpServer], None]] = None,
) -> None:
    """Serve initialized batch Maya; pump tools on this calling main thread.

    The caller owns Maya standalone initialization. This function owns only
    its server and dispatcher, and never starts the host's background driver.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("serve_headless() must run on Mayapy's main thread")
    if Version(core_version) < Version("0.19.64"):
        raise RuntimeError("serve_headless() requires dcc-mcp-core>=0.19.64 for standalone instance registration")
    dispatcher = BlockingDispatcher()
    host = MayaHost(dispatcher)
    if not host.is_background():
        host.stop()
        raise RuntimeError("serve_headless() requires initialized batch Maya; use start_server() in the GUI")
    server = None
    try:
        server = MayaMcpServer(
            port=port,
            gateway_port=gateway_port,
            registry_dir=registry_dir,
            host_dispatcher=dispatcher,
            instance_type="standalone",
        )
        server.register_builtin_actions(extra_skill_paths=extra_skill_paths)
        server.start()
        if on_started is not None:
            on_started(server)
        host.run_headless(stop_event=stop_event)
    finally:
        try:
            if server is not None:
                server.stop()
        finally:
            host.stop()
