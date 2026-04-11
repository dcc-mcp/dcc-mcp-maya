"""Delete the construction history on a Maya object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_history(
    object_name: str,
) -> dict:
    """Delete the construction history on a Maya object.

    Equivalent to *Edit > Delete by Type > History* in Maya.  Bakes the
    current deformed state into the mesh and removes all upstream history
    nodes, which can improve scene performance.

    Args:
        object_name: Name of the transform or shape node to process.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        cmds.delete(object_name, constructionHistory=True)

        return success_result(
            "Deleted construction history on '{}'".format(object_name),
            object_name=object_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_history failed")
        return error_result("Failed to delete history for {}".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_history`."""
    return delete_history(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_history()
    print(json.dumps(result))
