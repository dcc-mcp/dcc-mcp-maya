"""dcc-mcp-maya — Maya plugin for the DCC Model Context Protocol ecosystem.

Embeds a standards-compliant MCP Streamable HTTP server (2025-03-26 spec)
directly inside Maya using dcc-mcp-core.  No external gateway or dcc-mcp-ipc
required.

Quickstart (inside Maya's Python interpreter)::

    import dcc_mcp_maya
    handle = dcc_mcp_maya.start_server(port=8765)
    # MCP host connects to http://127.0.0.1:8765/mcp
    handle.shutdown()

"""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.__version__ import __version__
from dcc_mcp_maya.server import MayaMcpServer, start_server

__all__ = [
    "__version__",
    "MayaMcpServer",
    "start_server",
]
