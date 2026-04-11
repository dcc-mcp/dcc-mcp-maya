"""Combine multiple polygon meshes into a single mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
        return maya_error(
            "At least two objects are required for combine_meshes",
            "Provide a list of two or more polygon mesh names",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for obj in objects:
            if not cmds.objExists(obj):
                return maya_error(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist in the scene".format(obj),
                )

        kwargs = {}
        if name:
            kwargs["name"] = name
        result = cmds.polyUnite(*objects, constructionHistory=False, **kwargs) or []
        combined = result[0] if result else None
        if not combined:
            return maya_error(
                "polyUnite returned no result",
                "polyUnite did not produce any output mesh",
            )

        return maya_success(
            "Combined {} meshes into '{}'".format(len(objects), combined),
            combined_mesh=combined,
            input_count=len(objects),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to combine meshes")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`combine_meshes`."""
    return combine_meshes(**kwargs)


if __name__ == "__main__":
    import json

    result = combine_meshes()
    print(json.dumps(result))
