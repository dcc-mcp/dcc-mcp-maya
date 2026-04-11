"""Separate a polygon mesh containing disconnected shells into individual meshes."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
        return skill_error(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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

        return skill_success(
            "Separated '{}' into {} meshes".format(object_name, len(unique)),
            separated_meshes=unique,
            count=len(unique),
            prompt="Use combine_meshes to undo or cleanup_mesh on each piece.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to separate mesh '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`separate_mesh`."""
    return separate_mesh(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
