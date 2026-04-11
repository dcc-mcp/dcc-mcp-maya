"""List all Maya Muscle (cMuscleObject) nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_muscles() -> dict:
    """List cMuscleObject nodes with their basic attributes.

    Returns:
        ActionResultModel dict with ``context.muscles`` list and ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.loadPlugin("MayaMuscle", quiet=True)
        muscle_nodes = cmds.ls(type="cMuscleObject") or []

        results = []
        for node in muscle_nodes:
            parent = cmds.listRelatives(node, parent=True) or []
            try:
                radius0 = cmds.getAttr("{}.radius0".format(node))
                radius1 = cmds.getAttr("{}.radius1".format(node))
            except Exception:
                radius0 = radius1 = None

            results.append(
                {
                    "node": node,
                    "transform": parent[0] if parent else "",
                    "radius0": radius0,
                    "radius1": radius1,
                }
            )

        return maya_success(
            "Found {} muscle node(s)".format(len(results)),
            prompt="Use set_muscle_attribute to adjust simulation properties.",
            muscles=results,
            count=len(results),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list muscles")


def main(**kwargs):
    return list_muscles(**kwargs)


if __name__ == "__main__":
    import json

    result = list_muscles()
    print(json.dumps(result))
