"""Separate a polygon mesh containing disconnected shells into individual meshes."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    if not object_name:
        return maya_error(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

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

        return maya_success(
            "Separated '{}' into {} meshes".format(object_name, len(unique)),
            separated_meshes=unique,
            count=len(unique),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to separate mesh '{}'".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`separate_mesh`."""
    return separate_mesh(**kwargs)


if __name__ == "__main__":
    import json

    result = separate_mesh()
    print(json.dumps(result))
