"""List all cMuscleObject nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_muscles() -> dict:
    """List all Maya Muscle cMuscleObject nodes in the scene.

    Returns:
        ActionResultModel dict with ``context.muscles`` list and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        muscle_nodes = cmds.ls(type="cMuscleObject") or []

        result = []
        for node in muscle_nodes:
            info = {"node": node}
            # Attempt to read radius
            try:
                info["radius"] = cmds.getAttr("{}.radius".format(node))
            except Exception:
                info["radius"] = None
            # Attempt to find parent transform
            parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
            info["transform"] = parents[0] if parents else None
            result.append(info)

        return success_result(
            "Found {} muscle capsule(s)".format(len(result)),
            prompt=(
                "Use set_muscle_attribute to tune muscle parameters, or "
                "attach_muscle_to_skin to bind muscles to the skin deformer."
                if result
                else "No muscles found. Use create_muscle_capsule to add one."
            ),
            muscles=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_muscles failed")
        return error_result("Failed to list muscles", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_muscles(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_muscles()))
