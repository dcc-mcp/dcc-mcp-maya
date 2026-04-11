"""Apply cMuscleSystem deformer to a mesh to receive muscle influence."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def apply_muscle_skin(
    mesh: str,
    muscles: Optional[List[str]] = None,
) -> dict:
    """Attach cMuscleSystem deformer to a mesh.

    Args:
        mesh: Mesh transform or shape to deform.
        muscles: List of cMuscleObject nodes to connect. If empty, all scene muscles are used.

    Returns:
        ActionResultModel dict with ``context.system_node`` and ``context.muscles_connected``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return maya_error(
                "Mesh '{}' not found".format(mesh),
                "Verify the mesh name in the Outliner.",
            )

        cmds.loadPlugin("MayaMuscle", quiet=True)

        if not muscles:
            muscles = cmds.ls(type="cMuscleObject") or []

        if not muscles:
            return maya_error(
                "No muscle objects found or specified",
                "Create muscles first with create_muscle_capsule.",
            )

        muscle_parents = []
        for m in muscles:
            parent = cmds.listRelatives(m, parent=True) or []
            muscle_parents.append(parent[0] if parent else m)

        cmds.select(muscle_parents + [mesh], replace=True)
        mel.eval("cMuscle_applyMuscleSystem(0)")

        sys_nodes = cmds.ls(type="cMuscleSystem") or []
        sys_node = sys_nodes[-1] if sys_nodes else ""

        return maya_success(
            "cMuscleSystem '{}' applied to '{}'".format(sys_node, mesh),
            prompt="Muscle skin applied. Simulate or scrub the timeline to see secondary motion.",
            system_node=sys_node,
            mesh=mesh,
            muscles_connected=len(muscles),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to apply muscle skin to '{}'".format(mesh))

def main(**kwargs):
    return apply_muscle_skin(**kwargs)

if __name__ == "__main__":
    import json

    result = apply_muscle_skin("pSphere1")
    print(json.dumps(result))
