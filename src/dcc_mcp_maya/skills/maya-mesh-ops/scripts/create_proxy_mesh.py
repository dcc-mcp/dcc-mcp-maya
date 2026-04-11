"""Create a simplified proxy mesh from a polygon object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_proxy_mesh(
    object_name: str,
    reduction: float = 0.5,
    name: Optional[str] = None,
) -> dict:
    """Create a simplified proxy mesh from a polygon object.

    Uses ``cmds.polyReduce`` to produce a lower-resolution version of the
    source mesh.  The original object is left unchanged; a copy is created
    first and the reduction is applied to the copy.

    Args:
        object_name: Name of the source polygon mesh transform.
        reduction: Fraction of faces to *remove* (0.0 = no reduction,
            0.9 = remove 90% of faces).  Must be in range [0.0, 1.0).
            Default: 0.5.
        name: Optional name for the proxy mesh transform.  If None,
            Maya auto-generates a name.

    Returns:
        ActionResultModel dict with ``context.proxy_mesh``,
        ``context.original``, ``context.reduction``,
        ``context.face_count_before``, ``context.face_count_after``.
    """
    if not (0.0 <= reduction < 1.0):
        return skill_error(
            "Invalid reduction: {}".format(reduction),
            "reduction must be in range [0.0, 1.0)",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name), "")

        shapes = cmds.listRelatives(object_name, shapes=True, type="mesh") or []
        if not shapes:
            obj_type = cmds.objectType(object_name)
            if obj_type != "mesh":
                return skill_error("'{}' has no polygon mesh shape".format(object_name), "")

        # Record original face count
        face_count_before = cmds.polyEvaluate(object_name, face=True)
        face_count_before = face_count_before if isinstance(face_count_before, int) else 0

        # Duplicate source mesh
        dup_kwargs = {}
        if name:
            dup_kwargs["name"] = name
        dup_result = cmds.duplicate(object_name, **dup_kwargs)
        proxy = dup_result[0] if dup_result else None
        if not proxy:
            return skill_error("Failed to duplicate '{}'".format(object_name), "")

        # Apply polyReduce
        percentage = (1.0 - reduction) * 100.0
        cmds.polyReduce(
            proxy,
            percentage=percentage,
            triangulate=False,
            constructionHistory=False,
        )

        face_count_after = cmds.polyEvaluate(proxy, face=True)
        face_count_after = face_count_after if isinstance(face_count_after, int) else 0

        return skill_success(
            "Created proxy mesh '{}' from '{}' (reduction={})".format(proxy, object_name, reduction),
            proxy_mesh=proxy,
            original=object_name,
            reduction=reduction,
            face_count_before=face_count_before,
            face_count_after=face_count_after,
            prompt="Use swap_proxy in maya-proxy-mesh to toggle between proxy and hi-res.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create proxy mesh from '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_proxy_mesh`."""
    return create_proxy_mesh(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
