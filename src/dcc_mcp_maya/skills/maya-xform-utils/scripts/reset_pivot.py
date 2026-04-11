"""Move the pivot point to the bounding-box centre or world origin."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


def reset_pivot(
    objects: List[str],
    mode: str = "bbox_center",
) -> dict:
    """Reposition the pivot of each object.

    Args:
        objects: List of transform node names.
        mode: Where to place the pivot:
            - ``"bbox_center"`` — centre of the object's bounding box (default).
            - ``"world_origin"`` — place pivot at (0, 0, 0).
            - ``"bottom"`` — bottom-centre of the bounding box (useful for floor placement).

    Returns:
        ActionResultModel dict with ``context.updated_objects``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return error_result("No objects provided", "Pass at least one object name.").to_dict()

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Objects not found",
                "Missing: {}".format(", ".join(missing)),
            ).to_dict()

        valid_modes = {"bbox_center", "world_origin", "bottom"}
        if mode not in valid_modes:
            return error_result(
                "Invalid mode: {}".format(mode),
                "Choose from: {}".format(", ".join(sorted(valid_modes))),
            ).to_dict()

        updated = []
        for obj in objects:
            if mode == "world_origin":
                pivot = [0.0, 0.0, 0.0]
            else:
                bb = cmds.exactWorldBoundingBox(obj)
                # bb = [xmin, ymin, zmin, xmax, ymax, zmax]
                cx = (bb[0] + bb[3]) / 2.0
                cy_center = (bb[1] + bb[4]) / 2.0
                cz = (bb[2] + bb[5]) / 2.0
                if mode == "bottom":
                    pivot = [cx, bb[1], cz]
                else:  # bbox_center
                    pivot = [cx, cy_center, cz]

            cmds.xform(obj, worldSpace=True, pivots=pivot)
            updated.append({"name": obj, "pivot": pivot})

        return success_result(
            "Reset pivot for {} object(s) (mode={})".format(len(objects), mode),
            prompt="After adjusting the pivot, use freeze_transforms if you want to bake the new position.",
            updated_objects=updated,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("reset_pivot failed")
        return error_result("Failed to reset pivot", str(exc)).to_dict()


def main(**kwargs):
    return reset_pivot(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(reset_pivot(["pSphere1"], mode="bottom"), indent=2))
