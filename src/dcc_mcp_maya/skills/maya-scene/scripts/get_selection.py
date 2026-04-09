"""Return the current Maya selection."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_selection() -> dict:
    """Return the current Maya selection.

    Returns:
        ActionResultModel dict with ``context.selection`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        selection = cmds.ls(selection=True) or []
        return success_result(
            f"{len(selection)} objects selected",
            selection=selection,
            count=len(selection),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_selection failed")
        return error_result("Failed to get selection", str(exc)).to_dict()


def main(**kwargs):
    return get_selection(**kwargs)


if __name__ == "__main__":
    import json

    result = get_selection()
    print(json.dumps(result))
