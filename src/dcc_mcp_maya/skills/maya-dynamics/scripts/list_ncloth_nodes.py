"""List all nCloth shape nodes in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def list_ncloth_nodes() -> dict:
    """List all nCloth shape nodes in the current Maya scene.

    Returns basic information about each nCloth node including its name,
    parent transform, and the connected nucleus solver (if any).

    Returns:
        ActionResultModel dict with ``context.nodes`` (list of dicts) and
        ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ncloth_shapes = cmds.ls(type="nCloth") or []

        nodes = []
        for shape in ncloth_shapes:
            parent_transforms = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            parent = parent_transforms[0] if parent_transforms else None

            # Try to find connected nucleus solver
            nucleus = None
            connections = cmds.listConnections("{}.startFrame".format(shape), source=True, destination=False) or []
            for conn in connections:
                if cmds.objectType(conn) == "nucleus":
                    nucleus = conn
                    break

            nodes.append(
                {
                    "name": shape,
                    "transform": parent,
                    "nucleus": nucleus,
                }
            )

        return skill_success(
            "Found {} nCloth node(s) in scene".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list nCloth nodes")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_ncloth_nodes`."""
    return list_ncloth_nodes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
