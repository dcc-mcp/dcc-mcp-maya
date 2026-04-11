"""Combine multiple polygon meshes into a single mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def combine_meshes(
    objects,  # type: List[str]
    name=None,  # type: Optional[str]
):
    # type: (...) -> dict
    """Combine multiple polygon meshes into a single mesh.

    Uses ``cmds.polyUnite`` to merge the meshes and then deletes the original
    transform nodes.

    Args:
        objects: List of two or more polygon mesh transform names.
        name: Optional name for the resulting combined mesh.

    Returns:
        ActionResultModel dict with ``context.combined_mesh`` (name of the
        result) and ``context.input_count``.
    """
    if not objects or len(objects) < 2:
        return skill_error(
            "At least two objects are required for combine_meshes",
            "Provide a list of two or more polygon mesh names",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for obj in objects:
            err = validate_node_exists(cmds, obj)
            if err:
                return err

        kwargs = {}
        if name:
            kwargs["name"] = name
        result = cmds.polyUnite(*objects, constructionHistory=False, **kwargs) or []
        combined = result[0] if result else None
        if not combined:
            return skill_error(
                "polyUnite returned no result",
                "polyUnite did not produce any output mesh",
            )

        return skill_success(
            "Combined {} meshes into '{}'".format(len(objects), combined),
            combined_mesh=combined,
            input_count=len(objects),
            prompt="Use cleanup_mesh or assign_material to finalise the combined mesh.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to combine meshes")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`combine_meshes`."""
    return combine_meshes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
