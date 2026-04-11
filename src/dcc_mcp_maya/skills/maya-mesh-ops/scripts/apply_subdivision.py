"""Apply subdivision to a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def apply_subdivision(
    object_name: str,
    level: int = 1,
    method: str = "preview",
) -> dict:
    """Apply subdivision to a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        level: Subdivision level / divisions.  Default: 1.
        method: ``"preview"`` (displaySmoothMesh — non-destructive) or
            ``"subdivide"`` (polySubdivideFacet — destructive).
            Default: ``"preview"``.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if method not in ("preview", "subdivide"):
        return error_result(
            "Invalid method: {}".format(method),
            "Use 'preview' or 'subdivide'",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        shapes = cmds.listRelatives(object_name, shapes=True, type="mesh") or []
        if not shapes:
            if cmds.objectType(object_name) == "mesh":
                shapes = [object_name]
            else:
                return error_result("'{}' has no polygon mesh shape".format(object_name)).to_dict()

        shape = shapes[0]

        if method == "preview":
            cmds.setAttr("{}.displaySmoothMesh".format(shape), 2)
            cmds.setAttr("{}.smoothLevel".format(shape), level)
        else:
            cmds.polySubdivideFacet(object_name, dv=level)

        return success_result(
            "Subdivision applied to '{}' (method={}, level={})".format(object_name, method, level),
            object_name=object_name,
            method=method,
            level=level,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("apply_subdivision failed")
        return error_result("Failed to apply subdivision", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`apply_subdivision`."""
    return apply_subdivision(**kwargs)


if __name__ == "__main__":
    import json

    result = apply_subdivision()
    print(json.dumps(result))
