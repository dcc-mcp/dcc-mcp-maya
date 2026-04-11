"""Create an FFD (Free-Form Deformation) lattice on one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def create_lattice(
    objects: List[str],
    divisions: Optional[List[int]] = None,
    name: Optional[str] = None,
    local_scale: Optional[List[float]] = None,
) -> dict:
    """Create an FFD (Free-Form Deformation) lattice on one or more objects.

    Args:
        objects: List of mesh/surface names to enclose in the lattice.
        divisions: ``[s_divisions, t_divisions, u_divisions]`` for the
            lattice control-point grid.  Defaults to ``[2, 5, 2]``.
        name: Optional base name for the lattice node.
        local_scale: Optional ``[sx, sy, sz]`` local scale applied to the
            FFD base.  If ``None``, the bounding-box size is used.

    Returns:
        ActionResultModel dict with ``context.ffd_node``,
        ``context.lattice_node``, ``context.base_node``,
        ``context.objects``.
    """
    if not objects:
        return maya_error(
            "No objects specified",
            "Provide at least one object name in the 'objects' list",
        )

    divs = divisions if (divisions and len(divisions) == 3) else [2, 5, 2]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return maya_error(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist before creating a lattice",
            )

        ffd_kwargs = {
            "divisions": divs,
        }  # type: Dict
        if name:
            ffd_kwargs["name"] = name

        result = cmds.lattice(objects, **ffd_kwargs)
        # cmds.lattice returns [ffdNode, latticeShape, baseShape]
        ffd_node = result[0] if result else None
        lattice_node = result[1] if result and len(result) > 1 else None
        base_node = result[2] if result and len(result) > 2 else None

        if local_scale and lattice_node:
            cmds.setAttr("{}.sx".format(lattice_node), local_scale[0])
            cmds.setAttr("{}.sy".format(lattice_node), local_scale[1])
            cmds.setAttr("{}.sz".format(lattice_node), local_scale[2])

        return maya_success(
            "Created FFD lattice '{}' ({}) on {} object(s)".format(ffd_node, divs, len(objects)),
            ffd_node=ffd_node,
            lattice_node=lattice_node,
            base_node=base_node,
            objects=objects,
            divisions=divs,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create FFD lattice")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_lattice`."""
    return create_lattice(**kwargs)


if __name__ == "__main__":
    import json

    result = create_lattice()
    print(json.dumps(result))
