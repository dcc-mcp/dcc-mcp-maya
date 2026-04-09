"""Copy UV layout from one mesh to another via polyTransfer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (source, target):
            if not cmds.objExists(name):
                return error_result("Object not found: {}".format(name)).to_dict()

        kwargs = {
            "transferUVs": 1,
            "sampleSpace": 4,  # UV space
            "ch": False,
        }  # type: Dict
        if source_uv_set:
            kwargs["sourceUvSet"] = source_uv_set
        if target_uv_set:
            kwargs["targetUvSet"] = target_uv_set

        cmds.transferAttributes(source, target, **kwargs)

        return success_result(
            "Copied UVs from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            source_uv_set=source_uv_set,
            target_uv_set=target_uv_set,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("copy_uvs failed")
        return error_result("Failed to copy UVs", str(exc)).to_dict()


def main(**kwargs):
    return copy_uvs(**kwargs)


if __name__ == "__main__":
    import json

    result = copy_uvs()
    print(json.dumps(result))
