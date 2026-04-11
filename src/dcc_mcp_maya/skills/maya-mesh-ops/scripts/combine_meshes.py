"""Combine multiple polygon meshes into a single mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects or len(objects) < 2:
        return error_result(
            "At least two objects are required for combine_meshes",
            "Provide a list of two or more polygon mesh names",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for obj in objects:
            if not cmds.objExists(obj):
                return error_result(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist in the scene".format(obj),
                ).to_dict()

        kwargs = {}
        if name:
            kwargs["name"] = name
        result = cmds.polyUnite(*objects, constructionHistory=False, **kwargs) or []
        combined = result[0] if result else None
        if not combined:
            return error_result(
                "polyUnite returned no result",
                "polyUnite did not produce any output mesh",
            ).to_dict()

        return success_result(
            "Combined {} meshes into '{}'".format(len(objects), combined),
            combined_mesh=combined,
            input_count=len(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("combine_meshes failed")
        return error_result("Failed to combine meshes", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`combine_meshes`."""
    return combine_meshes(**kwargs)


if __name__ == "__main__":
    import json

    result = combine_meshes()
    print(json.dumps(result))
