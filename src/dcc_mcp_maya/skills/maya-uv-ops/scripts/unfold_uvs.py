"""Unfold the UV layout on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def unfold_uvs(
    object_name: str,
    iterations: int = 1,
    optimize_scale: bool = True,
) -> dict:
    """Unfold the UV layout on a polygon mesh.

    Uses ``cmds.u3dUnfold`` to iteratively unfold UV shells.

    Args:
        object_name: Transform or mesh shape name.
        iterations: Number of unfold iterations (1–100).  Default: 1.
        optimize_scale: When True, normalises UV shells after unfolding so
            they all have the same texel density.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.iterations``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if iterations < 1 or iterations > 100:
        return error_result(
            "Invalid iterations: {}".format(iterations),
            "iterations must be between 1 and 100",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        cmds.u3dUnfold(
            object_name,
            iterations=iterations,
            pack=False,
            borderintersection=True,
            triangleflip=True,
            mapsize=512,
            roomspace=0,
        )

        if optimize_scale:
            cmds.u3dOptimize(object_name, iterations=1, power=1, resultScale=1)

        return success_result(
            "Unfolded UVs on '{}' ({} iteration(s))".format(object_name, iterations),
            object_name=object_name,
            iterations=iterations,
            optimize_scale=optimize_scale,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("unfold_uvs failed")
        return error_result("Failed to unfold UVs on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`unfold_uvs`."""
    return unfold_uvs(**kwargs)


if __name__ == "__main__":
    import json

    result = unfold_uvs()
    print(json.dumps(result))
