"""Create a new vertex color set on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def create_color_set(
    object_name: str,
    color_set_name: str,
    representation: str = "RGBA",
) -> dict:
    """Create a new vertex color set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        color_set_name: Name for the new color set.
        representation: Color representation — ``"RGB"`` or ``"RGBA"``.
            Default: ``"RGBA"``.

    Returns:
        ActionResultModel dict.
    """

    valid_reps = ("RGB", "RGBA")
    if representation not in valid_reps:
        return skill_error(
            "Invalid representation: {}".format(representation),
            "Use one of: {}".format(", ".join(valid_reps)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
        if color_set_name in existing:
            return skill_error("Color set '{}' already exists on '{}'".format(color_set_name, object_name))

        cmds.polyColorSet(
            object_name,
            create=True,
            colorSet=color_set_name,
            representation=representation,
        )

        return skill_success(
            "Created color set '{}' on '{}'".format(color_set_name, object_name),
            object_name=object_name,
            color_set_name=color_set_name,
            representation=representation,
            prompt="Check the result with list_vertex_color or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create color set")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_color_set`."""
    return create_color_set(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
