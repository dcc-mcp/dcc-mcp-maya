"""Copy UV layout from one mesh to another via polyTransfer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


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

        err = batch_validate_nodes(cmds, [source, target])
        if err:
            return err

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

        return skill_success(
            "Copied UVs from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            source_uv_set=source_uv_set,
            target_uv_set=target_uv_set,
            prompt="Use layout_uvs to arrange or export_uv_snapshot to preview.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to copy UVs")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`copy_uvs`."""
    return copy_uvs(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
