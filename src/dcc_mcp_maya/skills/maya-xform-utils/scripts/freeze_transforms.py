"""Freeze translate, rotate, and/or scale transforms on one or more objects."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List

def freeze_transforms(
    objects: List[str],
    translate: bool = True,
    rotate: bool = True,
    scale: bool = True,
    apply: bool = True,
) -> dict:
    """Freeze transforms on the given objects.

    Zeroes out translate/rotate (values become 0) and normalises scale
    (values become 1) without moving the object in world space.

    Args:
        objects: List of transform node names to freeze.
        translate: Freeze translation if ``True``.
        rotate: Freeze rotation if ``True``.
        scale: Freeze scale if ``True``.
        apply: If ``True`` (default) actually apply the freeze.  Set to
            ``False`` to perform a dry-run that only validates inputs.

    Returns:
        ActionResultModel dict with ``context.frozen_objects``.
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

        if apply:
            cmds.makeIdentity(
                objects,
                apply=True,
                translate=translate,
                rotate=rotate,
                scale=scale,
                normal=False,
                preserveNormals=True,
            )

        frozen = []
        for obj in objects:
            entry = {"name": obj}
            if translate:
                entry["translate"] = list(cmds.getAttr("{}.translate".format(obj))[0])
            if rotate:
                entry["rotate"] = list(cmds.getAttr("{}.rotate".format(obj))[0])
            if scale:
                entry["scale"] = list(cmds.getAttr("{}.scale".format(obj))[0])
            frozen.append(entry)

        return maya_success(
            "Frozen transforms on {} object(s)".format(len(objects)),
            prompt="Use reset_pivot to also centre the pivot, or match_transforms to align to another object.",
            frozen_objects=frozen,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to freeze transforms")

def main(**kwargs):
    return freeze_transforms(**kwargs)

if __name__ == "__main__":
    import json

    print(json.dumps(freeze_transforms(["pSphere1"]), indent=2))
