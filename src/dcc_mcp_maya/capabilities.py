"""Maya DCC capabilities declaration using dcc-mcp-core's DccCapabilities.

This module provides a single factory function :func:`maya_capabilities` that
returns a ``DccCapabilities`` instance declaring what this Maya integration
supports.  The result is serialisable via ``to_dict()`` for cross-DCC protocol
use.

Supported capability flags:

- ``scene_manager``  — ``new_scene``, ``open_scene``, ``save_scene``, ``import_file``
- ``transform``      — ``get_transform`` / ``set_transform`` via maya-primitives skill
- ``hierarchy``      — ``group_objects``, ``parent_object``, DAG hierarchy queries
- ``selection``      — ``select_objects``, ``get_selection``, ``select_by_type``
- ``render_capture`` — ``render_frame`` via maya-render skill (headless-mode may skip)
- ``snapshot``       — ``playblast`` viewport screenshot
- ``undo_redo``      — Maya's native unlimited undo queue
- ``file_operations``— FBX / Alembic / OBJ import/export
- ``has_embedded_python`` — Maya ships its own CPython interpreter (mayapy)
- ``progress_reporting`` — ``cmds.progressWindow`` available inside Maya GUI
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["maya_capabilities", "MAYA_CAPABILITIES_DICT"]


def maya_capabilities():
    """Return a ``DccCapabilities`` instance for the Maya integration.

    All flags reflect capabilities available in Maya 2020+ (Python 3.7+).
    Renderer-specific flags (``render_capture``, ``snapshot``) require a
    running Maya session; the flags are still declared ``True`` because the
    code paths exist — callers may receive a skill_error at runtime if Maya
    is headless.

    Returns:
        ``dcc_mcp_core.DccCapabilities`` instance.

    Example::

        caps = maya_capabilities()
        print(caps.transform)          # True
        print(caps.to_dict())          # {...}
    """
    from dcc_mcp_core import DccCapabilities  # noqa: PLC0415

    return DccCapabilities(
        scene_manager=True,
        transform=True,
        hierarchy=True,
        selection=True,
        render_capture=True,
        snapshot=True,
        undo_redo=True,
        file_operations=True,
        has_embedded_python=True,
        progress_reporting=True,
        scene_info=True,
    )


# Pre-computed plain dict — available without importing dcc_mcp_core at import
# time.  Useful for fast serialisation or when dcc_mcp_core is unavailable.
MAYA_CAPABILITIES_DICT = {
    "scene_manager": True,
    "transform": True,
    "hierarchy": True,
    "selection": True,
    "render_capture": True,
    "snapshot": True,
    "undo_redo": True,
    "file_operations": True,
    "has_embedded_python": True,
    "progress_reporting": True,
    "scene_info": True,
}
