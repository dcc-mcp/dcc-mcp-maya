"""Connect two Maya node attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


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

        err = batch_validate_nodes(cmds, [source_attr, dest_attr])
        if err:
            return err

        cmds.connectAttr(source_attr, dest_attr, force=force)

        return skill_success(
            "Connected {} -> {}".format(source_attr, dest_attr),
            source_attr=source_attr,
            dest_attr=dest_attr,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_error(
            "Failed to connect {} -> {}".format(source_attr, dest_attr),
            str(exc),
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_attr`."""
    return connect_attr(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
