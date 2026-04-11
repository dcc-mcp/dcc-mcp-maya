"""Return the current Maya selection."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def get_selection() -> dict:
    """Return the current Maya selection.

    Returns:
        ActionResultModel dict with ``context.selection`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        selection = cmds.ls(selection=True) or []
        return maya_success(
            f"{len(selection)} objects selected",
            selection=selection,
            count=len(selection),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get selection")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_selection`."""
    return get_selection(**kwargs)

if __name__ == "__main__":
    import json

    result = get_selection()
    print(json.dumps(result))
