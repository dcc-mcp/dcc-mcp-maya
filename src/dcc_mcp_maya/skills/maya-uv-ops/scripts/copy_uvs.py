"""Copy UV layout from one mesh to another via polyTransfer."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def copy_uvs(
    source: str,
    target: str,
    source_uv_set: Optional[str] = None,
    target_uv_set: Optional[str] = None,
) -> dict:
    """Copy UV layout from one mesh to another via polyTransfer.

    Args:
        source: Source mesh transform or shape name.
        target: Target mesh transform or shape name.
        source_uv_set: UV set on the source to copy from.  If None, uses
            the current UV set.
        target_uv_set: UV set on the target to copy into.  If None, uses
            the current UV set.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (source, target):
            if not cmds.objExists(name):
                return maya_error("Object not found: {}".format(name), "'{}' does not exist".format(name))

        kwargs = {
            "transferUVs": 1,
            "sampleSpace": 4,  # UV space
            "ch": False,
        }
        if source_uv_set:
            kwargs["sourceUvSet"] = source_uv_set
        if target_uv_set:
            kwargs["targetUvSet"] = target_uv_set

        cmds.transferAttributes(source, target, **kwargs)

        return maya_success(
            "Copied UVs from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            source_uv_set=source_uv_set,
            target_uv_set=target_uv_set,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to copy UVs")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`copy_uvs`."""
    return copy_uvs(**kwargs)

if __name__ == "__main__":
    import json

    result = copy_uvs()
    print(json.dumps(result))
