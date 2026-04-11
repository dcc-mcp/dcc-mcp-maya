"""dcc-mcp-maya — Maya plugin for the DCC Model Context Protocol ecosystem.

Embeds a standards-compliant MCP Streamable HTTP server (2025-03-26 spec)
directly inside Maya using dcc-mcp-core.  No external gateway or dcc-mcp-ipc
required.

Quickstart (inside Maya's Python interpreter)::

    import dcc_mcp_maya
    handle = dcc_mcp_maya.start_server(port=8765)
    # MCP host connects to http://127.0.0.1:8765/mcp
    handle.shutdown()

Skill authoring helpers (for Maya skills developers)::

    from dcc_mcp_maya.api import (
        maya_success, maya_error, maya_from_exception, with_maya,
        require_param, validate_node_exists, validate_node_type,
    )

    @with_maya
    def create_sphere(radius: float = 1.0) -> dict:
        import maya.cmds as cmds
        result = cmds.polySphere(radius=radius)
        return maya_success("Created sphere", object_name=result[0])



"""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.__version__ import __version__
from dcc_mcp_maya.api import (
    MissingParamError,
    get_cmds,
    is_maya_available,
    maya_error,
    maya_from_exception,
    maya_success,
    missing_param_error,
    require_cmds,
    require_param,
    validate_node_exists,
    validate_node_type,
    with_maya,
)
from dcc_mcp_maya.server import MayaMcpServer, start_server, stop_server

__all__ = [
    "__version__",
    # Server
    "MayaMcpServer",
    "start_server",
    "stop_server",
    # Skill authoring helpers
    "maya_success",
    "maya_error",
    "maya_from_exception",
    "require_cmds",
    "get_cmds",
    "is_maya_available",
    "with_maya",
    # Parameter helpers
    "require_param",
    "missing_param_error",
    "MissingParamError",
    # Node validation helpers
    "validate_node_exists",
    "validate_node_type",
]
