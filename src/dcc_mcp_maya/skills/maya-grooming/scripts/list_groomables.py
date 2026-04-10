"""List all interactive groom shapes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_groomables() -> dict:
    """List all XGen interactive groom shapes in the scene.

    Returns:
        ActionResultModel dict with ``context.groomables`` list and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        groom_shapes = cmds.ls(type="igmGroom") or []

        result = []
        for shape in groom_shapes:
            info = {"shape": shape}
            # Attempt to find parent transform and connected mesh
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            info["transform"] = parents[0] if parents else None
            connections = cmds.listConnections(shape + ".inputMesh", source=True, destination=False) or []
            info["mesh"] = connections[0] if connections else None
            result.append(info)

        return success_result(
            "Found {} interactive groom shape(s)".format(len(result)),
            prompt=(
                "Use create_groom to add more groomables, or delete_groom to remove one."
                if result
                else "No groom shapes found. Use create_groom to add one."
            ),
            groomables=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_groomables failed")
        return error_result("Failed to list groomables", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_groomables(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_groomables()))
