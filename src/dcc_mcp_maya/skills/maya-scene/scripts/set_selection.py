"""Set the active Maya selection."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


def set_selection(objects: List[str]) -> dict:
    """Set the active Maya selection.

    Args:
        objects: List of object names to select.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.select(objects, replace=True)
        return success_result(
            f"Selected {len(objects)} objects",
            selection=objects,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_selection failed")
        return error_result("Failed to set selection", str(exc)).to_dict()


def main(**kwargs):
    return set_selection(**kwargs)


if __name__ == "__main__":
    import json

    result = set_selection()
    print(json.dumps(result))
