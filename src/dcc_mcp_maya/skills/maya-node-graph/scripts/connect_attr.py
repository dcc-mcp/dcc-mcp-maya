"""Connect two Maya node attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def connect_attr(
    source_attr: str,
    dest_attr: str,
    force: bool = False,
) -> dict:
    """Connect two Maya node attributes.

    Args:
        source_attr: Full attribute path of the driver, e.g.
            ``"pSphere1.translateX"``.
        dest_attr: Full attribute path of the driven attribute.
        force: If True, break any existing connection on *dest_attr* before
            connecting.  Default: False.

    Returns:
        ActionResultModel dict with ``context.source_attr`` and
        ``context.dest_attr``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source_attr):
            return maya_error(
                "Source attribute not found: {}".format(source_attr),
                "'{}' does not exist".format(source_attr),
            )

        if not cmds.objExists(dest_attr):
            return maya_error(
                "Destination attribute not found: {}".format(dest_attr),
                "'{}' does not exist".format(dest_attr),
            )

        cmds.connectAttr(source_attr, dest_attr, force=force)

        return maya_success(
            "Connected {} -> {}".format(source_attr, dest_attr),
            source_attr=source_attr,
            dest_attr=dest_attr,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error(
            "Failed to connect {} -> {}".format(source_attr, dest_attr),
            str(exc),
        )

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_attr`."""
    return connect_attr(**kwargs)

if __name__ == "__main__":
    import json

    result = connect_attr()
    print(json.dumps(result))
