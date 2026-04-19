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
    batch_validate_nodes,
    bounding_box_from_node,
    build_context_dict,
    ensure_valid_name,
    get_cmds,
    get_param_list,
    is_maya_available,
    maya_capabilities,
    maya_error,
    maya_from_exception,
    maya_success,
    maya_warning,
    missing_param_error,
    object_transform_from_node,
    require_any_param,
    require_cmds,
    require_param,
    scene_object_from_node,
    validate_node_exists,
    validate_node_type,
    with_maya,
)
from dcc_mcp_maya.dispatcher import (
    MayaStandaloneDispatcher,
    MayaUiDispatcher,
    MayaUiPump,
    create_dispatcher,
)
from dcc_mcp_maya.server import MayaMcpServer, start_server, stop_server

__all__ = [
    "__version__",
    # Server
    "MayaMcpServer",
    "start_server",
    "stop_server",
    # Dispatchers
    "MayaUiDispatcher",
    "MayaUiPump",
    "MayaStandaloneDispatcher",
    "create_dispatcher",
    # Skill authoring helpers
    "maya_success",
    "maya_error",
    "maya_warning",
    "maya_from_exception",
    "require_cmds",
    "get_cmds",
    "is_maya_available",
    "with_maya",
    # Parameter helpers
    "require_param",
    "require_any_param",
    "get_param_list",
    "missing_param_error",
    "MissingParamError",
    # Node validation helpers
    "validate_node_exists",
    "validate_node_type",
    "batch_validate_nodes",
    # Name and context helpers
    "ensure_valid_name",
    "build_context_dict",
    # Cross-DCC data model helpers
    "scene_object_from_node",
    "object_transform_from_node",
    "bounding_box_from_node",
    # DCC capabilities
    "maya_capabilities",
]
