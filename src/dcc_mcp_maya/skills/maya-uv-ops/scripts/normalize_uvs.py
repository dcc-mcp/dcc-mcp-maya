"""Normalize UV coordinates to fit within the 0-1 UV tile."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def normalize_uvs(
    object_name: str,
    layout_u: float = 1.0,
    layout_v: float = 1.0,
    preserve_aspect: bool = True,
) -> dict:
    """Normalize UV coordinates to fit within the 0-1 UV tile.

    Args:
        object_name: Transform or mesh shape name.
        layout_u: Target U dimension (0 < value <= 1).  Default: 1.0.
        layout_v: Target V dimension (0 < value <= 1).  Default: 1.0.
        preserve_aspect: When True, scale uniformly to preserve aspect ratio.
            Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """

    if not (0 < layout_u <= 1):
        return skill_error(
            "Invalid layout_u: {}".format(layout_u),
            "layout_u must be in range (0, 1]",
        )
    if not (0 < layout_v <= 1):
        return skill_error(
            "Invalid layout_v: {}".format(layout_v),
            "layout_v must be in range (0, 1]",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        cmds.polyNormalizeUV(
            object_name,
            normalizeType=1,
            preserveAspectRatio=preserve_aspect,
            centerOnTile=True,
            ch=False,
        )

        return skill_success(
            "Normalized UVs on '{}' (layout_u={}, layout_v={})".format(object_name, layout_u, layout_v),
            object_name=object_name,
            layout_u=layout_u,
            layout_v=layout_v,
            preserve_aspect=preserve_aspect,
            prompt="Use layout_uvs or export_uv_snapshot to verify.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to normalize UVs on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`normalize_uvs`."""
    return normalize_uvs(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
