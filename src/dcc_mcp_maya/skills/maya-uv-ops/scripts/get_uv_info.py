"""Query UV sets and coordinates on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, validate_node_exists


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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
                return maya_error("UV set '{}' not found on '{}'".format(uv_set, object_name))
            u_coords = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, uValue=True) or []
            _ = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, vValue=True) or []
            result_kwargs["uv_count"] = len(u_coords)
            result_kwargs["queried_uv_set"] = uv_set

        return maya_success(
            "UV info for '{}'".format(object_name),
            **result_kwargs,
            prompt="Check the result with list_uv_ops or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get UV info")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_uv_info`."""
    return get_uv_info(**kwargs)


if __name__ == "__main__":
    import json

    result = get_uv_info()
    print(json.dumps(result))
