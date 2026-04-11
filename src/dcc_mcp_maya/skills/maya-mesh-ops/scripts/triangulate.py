"""Triangulate all faces of a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def triangulate(object_name: str) -> dict:
    """Triangulate all faces of a polygon mesh.

    Args:
        object_name: Transform or mesh name.

    Returns:
        ActionResultModel dict with face counts before and after.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        before = cmds.polyEvaluate(object_name, face=True)
        cmds.polyTriangulate(object_name)
        after = cmds.polyEvaluate(object_name, face=True)

        before_count = before if isinstance(before, int) else 0
        after_count = after if isinstance(after, int) else 0

        return skill_success(
            "Triangulated '{}': {} -> {} faces".format(object_name, before_count, after_count),
            object_name=object_name,
            face_count_before=before_count,
            face_count_after=after_count,
            prompt="Use export_shot_fbx or get_poly_count to verify the result.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to triangulate")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`triangulate`."""
    return triangulate(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
