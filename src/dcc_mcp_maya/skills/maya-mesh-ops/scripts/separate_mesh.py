"""Separate a polygon mesh containing disconnected shells into individual meshes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def separate_mesh(
    object_name,  # type: str
):
    # type: (...) -> dict
    """Separate a polygon mesh that contains disconnected shells into individual meshes.

    Uses ``cmds.polySeparate`` to split each disconnected shell into its own
    transform node.

    Args:
        object_name: Name of the polygon mesh transform to separate.

    Returns:
        ActionResultModel dict with ``context.separated_meshes`` (list of
        result transform names) and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not object_name:
        return error_result(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        result = cmds.polySeparate(object_name, constructionHistory=False) or []
        # polySeparate returns shape nodes; get their parent transforms
        separated = []
        for node in result:
            if cmds.objectType(node) == "transform":
                separated.append(node)
            else:
                parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
                if parents:
                    separated.append(parents[0])

        # Deduplicate while preserving order
        seen = set()  # type: set
        unique = []
        for s in separated:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return success_result(
            "Separated '{}' into {} meshes".format(object_name, len(unique)),
            separated_meshes=unique,
            count=len(unique),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("separate_mesh failed")
        return error_result("Failed to separate mesh '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`separate_mesh`."""
    return separate_mesh(**kwargs)


if __name__ == "__main__":
    import json

    result = separate_mesh()
    print(json.dumps(result))
