"""Create an FFD (Free-Form Deformation) lattice on one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


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
        return skill_error(
            "No objects specified",
            "Provide at least one object name in the 'objects' list",
        )

    divs = divisions if (divisions and len(divisions) == 3) else [2, 5, 2]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, list(objects))
        if err:
            return err

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

        return skill_success(
            "Created FFD lattice '{}' ({}) on {} object(s)".format(ffd_node, divs, len(objects)),
            ffd_node=ffd_node,
            lattice_node=lattice_node,
            base_node=base_node,
            objects=objects,
            divisions=divs,
            prompt="Check the result with list_deformers or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create FFD lattice")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_lattice`."""
    return create_lattice(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
