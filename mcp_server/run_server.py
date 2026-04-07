"""DCC-MCP-Maya MCP HTTP Streamable Server.

This server runs OUTSIDE Maya (as a standalone Python process) and exposes all
Maya operations as MCP tools via HTTP Streamable transport.

Agents like Claude Desktop, OpenClaw, Cursor, etc. can connect to this server
at http://localhost:PORT/mcp/v1 (Streamable HTTP) or use SSE.

Usage:
    python run_server.py [--host HOST] [--port PORT] [--maya-host H] [--maya-port P]

    # Or with the bundled launcher:
    start_mcp_server.bat          (Windows)
    bash start_mcp_server.sh      (macOS/Linux)
"""

# Import built-in modules
import argparse
import logging
import sys

# Import third-party modules
import fastmcp
from fastmcp import FastMCP

# Import local modules — allow running from the bundle layout
import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
_src = _os.path.join(_os.path.dirname(_here), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from dcc_mcp_maya.adapter import MayaAdapter  # noqa: E402

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dcc_mcp_maya.mcp_server")

# ── MCP Server Definition ─────────────────────────────────────────────────────
mcp = FastMCP(
    name="dcc-mcp-maya",
    version="0.1.0",
    description=(
        "Maya MCP server. Exposes Maya scene management, primitive creation, "
        "MEL execution and extensible action system via Model Context Protocol."
    ),
)

# Lazy adapter — created once on first use
_adapter: MayaAdapter | None = None
_maya_host: str = "localhost"
_maya_port: int | None = None


def _get_adapter() -> MayaAdapter:
    global _adapter
    if _adapter is None or not _adapter._ensure_connected():
        _adapter = MayaAdapter(host=_maya_host, port=_maya_port)
    return _adapter


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_scene_info() -> dict:
    """Get information about the current Maya scene.

    Returns scene path, modified state, selection, and object count.
    """
    result = _get_adapter().get_scene_info()
    return result.model_dump()


@mcp.tool()
def get_session_info() -> dict:
    """Get Maya session information (version, OS, project path, Python version)."""
    result = _get_adapter().get_session_info()
    return result.model_dump()


@mcp.tool()
def get_maya_info() -> dict:
    """Get Maya application information (version, API version, OS)."""
    return _get_adapter().get_application_info()


@mcp.tool()
def execute_python(code: str, context: dict = None) -> dict:
    """Execute arbitrary Python code inside Maya.

    Args:
        code: Python source code to run inside Maya's interpreter.
        context: Optional dict of variables to inject into the execution scope.

    Returns:
        ActionResultModel with execution result or error info.

    Example:
        execute_python("result = cmds.ls(sl=True)")
    """
    from dcc_mcp_core import ActionResultModel
    adapter = _get_adapter()
    if not adapter._ensure_connected():
        return ActionResultModel(
            success=False, message="Not connected to Maya", error="ConnectionError"
        ).model_dump()
    try:
        raw = adapter.client.root.execute_python(code, context or {})
        return ActionResultModel(
            success=True,
            message="Python executed",
            context={"result": raw},
        ).model_dump()
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e)).model_dump()


@mcp.tool()
def execute_mel(script: str) -> dict:
    """Execute a MEL script inside Maya.

    Args:
        script: MEL script string (e.g. "polySphere -r 1 -name mySphere;").

    Returns:
        ActionResultModel with result or error info.
    """
    result = _get_adapter().execute_mel(script)
    return result.model_dump()


@mcp.tool()
def execute_maya_cmd(command: str, args: list = None, kwargs: dict = None) -> dict:
    """Execute a maya.cmds command.

    Args:
        command: Name of the maya.cmds function (e.g. "polySphere", "ls", "select").
        args: Positional arguments list.
        kwargs: Keyword arguments dict.

    Returns:
        ActionResultModel with result or error info.

    Example:
        execute_maya_cmd("ls", kwargs={"selection": true})
    """
    result = _get_adapter().execute_maya_cmd(command, *(args or []), **(kwargs or {}))
    return result.model_dump()


@mcp.tool()
def create_primitive(
    primitive_type: str,
    name: str = "",
    radius: float = 1.0,
    width: float = 1.0,
    height: float = 1.0,
    depth: float = 1.0,
) -> dict:
    """Create a polygon primitive in Maya.

    Args:
        primitive_type: One of "sphere", "cube", "cylinder", "cone", "plane", "torus".
        name: Optional name for the created object.
        radius: Radius (for sphere, cylinder, cone, torus).
        width: Width (for cube, plane).
        height: Height (for cube, cylinder, cone, plane).
        depth: Depth (for cube).

    Returns:
        ActionResultModel with created object names.
    """
    extra = {}
    if name:
        extra["name"] = name
    primitive_type = primitive_type.lower()
    if primitive_type in ("sphere", "cylinder", "cone", "torus"):
        extra["radius"] = radius
    if primitive_type in ("cube",):
        extra["width"] = width
        extra["height"] = height
        extra["depth"] = depth
    if primitive_type in ("cylinder", "cone"):
        extra["height"] = height
    if primitive_type in ("plane",):
        extra["width"] = width
        extra["height"] = height
    result = _get_adapter().create_primitive(primitive_type, **extra)
    return result.model_dump()


@mcp.tool()
def list_actions() -> dict:
    """List all registered Maya MCP actions available in the service."""
    result = _get_adapter().list_actions()
    return result.model_dump()


@mcp.tool()
def call_action(action_name: str, action_kwargs: dict = None) -> dict:
    """Call a registered Maya MCP action by name.

    Args:
        action_name: Name of the action (e.g. "create_sphere", "list_objects").
        action_kwargs: Keyword arguments to pass to the action.

    Returns:
        ActionResultModel with action result.
    """
    result = _get_adapter().call_action(action_name, **(action_kwargs or {}))
    return result.model_dump()


@mcp.tool()
def list_scene_objects(object_type: str = "", dag: bool = True) -> dict:
    """List all objects in the current Maya scene.

    Args:
        object_type: Optional filter by Maya node type (e.g. "mesh", "camera", "joint").
        dag: If True, only return DAG nodes (default True).

    Returns:
        ActionResultModel with list of object names.
    """
    result = _get_adapter().call_action("list_objects", object_type=object_type, dag=dag)
    return result.model_dump()


@mcp.tool()
def get_selection() -> dict:
    """Get the current selection in Maya."""
    result = _get_adapter().call_action("get_selection")
    return result.model_dump()


@mcp.tool()
def set_selection(objects: list) -> dict:
    """Set the current selection in Maya.

    Args:
        objects: List of object names to select.
    """
    result = _get_adapter().call_action("set_selection", objects=objects)
    return result.model_dump()


@mcp.tool()
def new_scene(force: bool = False) -> dict:
    """Create a new Maya scene.

    Args:
        force: If True, discard unsaved changes without prompting.
    """
    result = _get_adapter().call_action("new_scene", force=force)
    return result.model_dump()


@mcp.tool()
def save_scene(file_path: str = "", file_type: str = "mayaBinary") -> dict:
    """Save the current Maya scene.

    Args:
        file_path: Path to save to. If empty, saves to current path.
        file_type: "mayaBinary" or "mayaAscii".
    """
    result = _get_adapter().call_action("save_scene", file_path=file_path, file_type=file_type)
    return result.model_dump()


# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("maya://scene/info")
def scene_info_resource() -> str:
    """Current Maya scene information as a resource."""
    result = _get_adapter().get_scene_info()
    import json
    return json.dumps(result.context or {}, indent=2)


@mcp.resource("maya://session/info")
def session_info_resource() -> str:
    """Current Maya session information as a resource."""
    result = _get_adapter().get_session_info()
    import json
    return json.dumps(result.context or {}, indent=2)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _maya_host, _maya_port

    parser = argparse.ArgumentParser(
        description="DCC-MCP-Maya MCP HTTP Streamable Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="0.0.0.0", help="MCP server bind host")
    parser.add_argument("--port", type=int, default=8765, help="MCP server port")
    parser.add_argument("--maya-host", default="localhost", help="Maya RPyC service host")
    parser.add_argument("--maya-port", type=int, default=None, help="Maya RPyC service port (auto-discover if omitted)")
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse"],
        default="streamable-http",
        help="MCP transport type",
    )
    args = parser.parse_args()

    _maya_host = args.maya_host
    _maya_port = args.maya_port

    logger.info(
        "Starting DCC-MCP-Maya MCP server  transport=%s  %s:%s  →  maya@%s:%s",
        args.transport, args.host, args.port, _maya_host, _maya_port or "auto",
    )
    print(f"\n  MCP Endpoint: http://{args.host}:{args.port}/mcp/v1")
    print(f"  Transport:    {args.transport}")
    print(f"  Maya:         {_maya_host}:{_maya_port or 'auto-discover'}")
    print(f"\n  Add to Claude Desktop / OpenClaw:")
    print(f'  {{"url": "http://localhost:{args.port}/mcp/v1", "transport": "{args.transport}"}}')
    print()

    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
