"""Create a new UV set on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_uv_set(object_name: str, uv_set_name: str, copy_from: Optional[str] = None) -> dict:
    """Create a new UV set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name for the new UV set.
        copy_from: Optional existing UV set name to copy UVs from.

    Returns:
        ActionResultModel dict with ``context.uv_set_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name in existing:
            return error_result("UV set '{}' already exists on '{}'".format(uv_set_name, object_name)).to_dict()

        if copy_from:
            if copy_from not in existing:
                return error_result("Source UV set '{}' not found on '{}'".format(copy_from, object_name)).to_dict()
            cmds.polyUVSet(object_name, copy=True, uvSet=copy_from, newUVSet=uv_set_name)
        else:
            cmds.polyUVSet(object_name, create=True, uvSet=uv_set_name)

        return success_result(
            "Created UV set '{}' on '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
            copied_from=copy_from,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_uv_set failed")
        return error_result("Failed to create UV set", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_uv_set`."""
    return create_uv_set(**kwargs)


if __name__ == "__main__":
    import json

    result = create_uv_set()
    print(json.dumps(result))
