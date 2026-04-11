"""Query UV sets and coordinates on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_uv_info(object_name: str, uv_set: Optional[str] = None) -> dict:
    """Query UV sets and coordinates on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set: UV set name to query coordinates from.  If None, returns
            info about all UV sets without coordinate data.

    Returns:
        ActionResultModel dict with ``context.uv_sets``, ``context.current_uv_set``,
        and optionally ``context.uv_count`` / ``context.uvs``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        uv_sets = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        current_set = cmds.polyUVSet(object_name, query=True, currentUVSet=True)
        if isinstance(current_set, list):
            current_set = current_set[0] if current_set else None

        result_kwargs = {
            "uv_sets": uv_sets,
            "current_uv_set": current_set,
            "uv_set_count": len(uv_sets),
        }  # type: Dict

        if uv_set:
            if uv_set not in uv_sets:
                return error_result("UV set '{}' not found on '{}'".format(uv_set, object_name)).to_dict()
            u_coords = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, uValue=True) or []
            _ = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, vValue=True) or []
            result_kwargs["uv_count"] = len(u_coords)
            result_kwargs["queried_uv_set"] = uv_set

        return success_result("UV info for '{}'".format(object_name), **result_kwargs).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_uv_info failed")
        return error_result("Failed to get UV info", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_uv_info`."""
    return get_uv_info(**kwargs)


if __name__ == "__main__":
    import json

    result = get_uv_info()
    print(json.dumps(result))
