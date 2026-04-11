"""Apply subdivision to a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    if method not in ("preview", "subdivide"):
        return maya_error(
            "Invalid method: {}".format(method),
            "Use 'preview' or 'subdivide'",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error("Object not found: {}".format(object_name), "")

        shapes = cmds.listRelatives(object_name, shapes=True, type="mesh") or []
        if not shapes:
            if cmds.objectType(object_name) == "mesh":
                shapes = [object_name]
            else:
                return maya_error("'{}' has no polygon mesh shape".format(object_name), "")

        shape = shapes[0]

        if method == "preview":
            cmds.setAttr("{}.displaySmoothMesh".format(shape), 2)
            cmds.setAttr("{}.smoothLevel".format(shape), level)
        else:
            cmds.polySubdivideFacet(object_name, dv=level)

        return maya_success(
            "Subdivision applied to '{}' (method={}, level={})".format(object_name, method, level),
            object_name=object_name,
            method=method,
            level=level,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to apply subdivision")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`apply_subdivision`."""
    return apply_subdivision(**kwargs)


if __name__ == "__main__":
    import json

    result = apply_subdivision()
    print(json.dumps(result))
