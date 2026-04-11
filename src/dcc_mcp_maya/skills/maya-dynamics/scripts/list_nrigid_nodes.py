"""List all nRigid (passive collider) shape nodes in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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


def list_nrigid_nodes():
    # type: () -> dict
    """List all nRigid (passive collider) shape nodes in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.nodes`` (list of dicts with
        ``name``, ``transform``, ``nucleus``) and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nrigid_shapes = cmds.ls(type="nRigid") or []

        nodes = []
        for shape in nrigid_shapes:
            parent_transforms = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            parent = parent_transforms[0] if parent_transforms else None

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

        return maya_success(
            "Found {} nRigid node(s) in scene".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list nRigid nodes")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_nrigid_nodes`."""
    return list_nrigid_nodes(**kwargs)


if __name__ == "__main__":
    import json

    result = list_nrigid_nodes()
    print(json.dumps(result))
