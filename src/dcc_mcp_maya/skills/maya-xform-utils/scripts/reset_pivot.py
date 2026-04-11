"""Move the pivot point to the bounding-box centre or world origin."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return maya_error("No objects provided", "Pass at least one object name.")

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return maya_error(
                "Objects not found",
                "Missing: {}".format(", ".join(missing)),
            )

        valid_modes = {"bbox_center", "world_origin", "bottom"}
        if mode not in valid_modes:
            return maya_error(
                "Invalid mode: {}".format(mode),
                "Choose from: {}".format(", ".join(sorted(valid_modes))),
            )

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

        return maya_success(
            "Reset pivot for {} object(s) (mode={})".format(len(objects), mode),
            prompt="After adjusting the pivot, use freeze_transforms if you want to bake the new position.",
            updated_objects=updated,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to reset pivot")


def main(**kwargs):
    return reset_pivot(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(reset_pivot(["pSphere1"], mode="bottom"), indent=2))
