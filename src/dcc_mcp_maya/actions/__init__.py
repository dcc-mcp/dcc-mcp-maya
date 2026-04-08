"""Built-in Maya actions for the MCP server.

All functions in this package are registered as MCP tools when
``MayaMcpServer.register_builtin_actions()`` is called.
"""

# Import future modules
from __future__ import annotations

from dcc_mcp_maya.actions.primitives import (
    create_cube,
    create_cylinder,
    create_sphere,
    delete_objects,
    set_transform,
)
from dcc_mcp_maya.actions.scene import (
    get_selection,
    get_session_info,
    list_objects,
    new_scene,
    open_scene,
    save_scene,
    set_selection,
)
from dcc_mcp_maya.actions.scripting import execute_mel, execute_python

__all__ = [
    # scene
    "new_scene",
    "save_scene",
    "open_scene",
    "list_objects",
    "get_selection",
    "set_selection",
    "get_session_info",
    # primitives
    "create_sphere",
    "create_cube",
    "create_cylinder",
    "delete_objects",
    "set_transform",
    # scripting
    "execute_mel",
    "execute_python",
]


def register_all(registry) -> None:
    """Register all built-in Maya actions into *registry*.

    Args:
        registry: An ``ActionRegistry`` instance from ``dcc_mcp_core``.
    """
    _ACTIONS = [
        # ── scene ──────────────────────────────────────────────────────────
        ("new_scene", "Create a new Maya scene", "scene", ["scene", "new"]),
        ("save_scene", "Save the current scene to disk", "scene", ["scene", "save", "io"]),
        ("open_scene", "Open a scene file", "scene", ["scene", "open", "io"]),
        ("list_objects", "List objects in the scene", "scene", ["scene", "query", "list"]),
        ("get_selection", "Get the current selection", "scene", ["scene", "query", "selection"]),
        ("set_selection", "Set the active selection", "scene", ["scene", "selection"]),
        ("get_session_info", "Get Maya version and scene info", "scene", ["scene", "query", "info"]),
        # ── primitives ─────────────────────────────────────────────────────
        ("create_sphere", "Create a polygon sphere", "geometry", ["create", "mesh", "sphere"]),
        ("create_cube", "Create a polygon cube", "geometry", ["create", "mesh", "cube"]),
        ("create_cylinder", "Create a polygon cylinder", "geometry", ["create", "mesh", "cylinder"]),
        ("delete_objects", "Delete objects from the scene", "geometry", ["delete", "mesh"]),
        ("set_transform", "Set translate/rotate/scale on an object", "geometry", ["transform", "move"]),
        # ── scripting ──────────────────────────────────────────────────────
        ("execute_mel", "Execute a MEL script", "scripting", ["mel", "script", "execute"]),
        ("execute_python", "Execute Python inside Maya", "scripting", ["python", "script", "execute"]),
    ]

    for name, description, category, tags in _ACTIONS:
        registry.register(
            name,
            description=description,
            category=category,
            tags=tags,
            dcc="maya",
            version="1.0.0",
        )
