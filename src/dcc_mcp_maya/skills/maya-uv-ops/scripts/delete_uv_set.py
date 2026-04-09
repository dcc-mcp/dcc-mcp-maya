"""Delete a UV set from a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_uv_set(object_name: str, uv_set_name: str) -> dict:
    """Delete a UV set from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name of the UV set to delete.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name not in existing:
            return error_result("UV set '{}' not found on '{}'".format(uv_set_name, object_name)).to_dict()

        # Protect the only remaining UV set
        if len(existing) <= 1:
            return error_result("Cannot delete the only UV set on '{}'".format(object_name)).to_dict()

        cmds.polyUVSet(object_name, delete=True, uvSet=uv_set_name)

        return success_result(
            "Deleted UV set '{}' from '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_uv_set failed")
        return error_result("Failed to delete UV set", str(exc)).to_dict()


def main(**kwargs):
    return delete_uv_set(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_uv_set()
    print(json.dumps(result))
