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
from dcc_mcp_maya._env import (
    ENV_CURSOR_SAFE_TOOL_NAMES,
    ENV_TOOL_EXPOSURE,
    VALID_TOOL_EXPOSURE_MODES,
    resolve_cursor_safe_tool_names,
    resolve_tool_exposure,
)
from dcc_mcp_maya._project_tools import (
    ENV_PROJECT_TOOLS,
    MayaSceneResolver,
    ProjectToolsIntegration,
)
from dcc_mcp_maya._project_tools import (
    attach_to_server as attach_project_tools,
)
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
    maya_typed_success,
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
from dcc_mcp_maya.capability_manifest import (
    CapabilityRecord,
    MayaCapabilityManifestBuilder,
    build_manifest_payload,
    register_capability_mcp_tool,
)
from dcc_mcp_maya.context_snapshot import (
    MayaContextSnapshotProvider,
    collect_gateway_metadata,
    make_snapshot_provider,
)
from dcc_mcp_maya.dispatcher import (
    MayaStandaloneDispatcher,
    MayaUiDispatcher,
    MayaUiPump,
    PyPumpedDispatcher,
    PyStandaloneDispatcher,
    _CorePump,
    check_maya_cancelled,
    create_dispatcher,
    create_pumped_dispatcher,
)
from dcc_mcp_maya.host import MayaCallableDispatcher, MayaHost
from dcc_mcp_maya.server import MayaMcpServer, start_server, stop_server

__all__ = [
    "__version__",
    # Server
    "MayaMcpServer",
    "start_server",
    "stop_server",
    # Host adapter (core 0.14.23 main-thread dispatcher)
    "MayaHost",
    "MayaCallableDispatcher",
    # Dispatchers — Python-side (callable dispatch, main-thread affinity)
    "MayaUiDispatcher",
    "MayaUiPump",
    "MayaStandaloneDispatcher",
    "create_dispatcher",
    "check_maya_cancelled",
    # Dispatchers — Rust-backed (string-payload dispatch, dcc-mcp-core 0.14.14+)
    "PyPumpedDispatcher",
    "PyStandaloneDispatcher",
    "_CorePump",
    "create_pumped_dispatcher",
    # Skill authoring helpers
    "maya_success",
    "maya_error",
    "maya_warning",
    "maya_from_exception",
    "maya_typed_success",
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
    # Capability manifest (issue #163)
    "CapabilityRecord",
    "MayaCapabilityManifestBuilder",
    "build_manifest_payload",
    "register_capability_mcp_tool",
    # Context snapshot (issue #165)
    "MayaContextSnapshotProvider",
    "collect_gateway_metadata",
    "make_snapshot_provider",
    # Project-state persistence (issue #576 / core 0.14.21)
    "ENV_PROJECT_TOOLS",
    "MayaSceneResolver",
    "ProjectToolsIntegration",
    "attach_project_tools",
    # Gateway tool-exposure + cursor-safe naming (core 0.14.22)
    "ENV_TOOL_EXPOSURE",
    "ENV_CURSOR_SAFE_TOOL_NAMES",
    "VALID_TOOL_EXPOSURE_MODES",
    "resolve_tool_exposure",
    "resolve_cursor_safe_tool_names",
]
