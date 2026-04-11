"""Connect two Maya node attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source_attr):
            return error_result(
                "Source attribute not found: {}".format(source_attr),
                "'{}' does not exist".format(source_attr),
            ).to_dict()

        if not cmds.objExists(dest_attr):
            return error_result(
                "Destination attribute not found: {}".format(dest_attr),
                "'{}' does not exist".format(dest_attr),
            ).to_dict()

        cmds.connectAttr(source_attr, dest_attr, force=force)

        return success_result(
            "Connected {} -> {}".format(source_attr, dest_attr),
            source_attr=source_attr,
            dest_attr=dest_attr,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("connect_attr failed")
        return error_result(
            "Failed to connect {} -> {}".format(source_attr, dest_attr),
            str(exc),
        ).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_attr`."""
    return connect_attr(**kwargs)


if __name__ == "__main__":
    import json

    result = connect_attr()
    print(json.dumps(result))
