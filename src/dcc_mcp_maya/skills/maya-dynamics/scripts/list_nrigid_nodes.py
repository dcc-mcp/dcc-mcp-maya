"""List all nRigid (passive collider) shape nodes in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} nRigid node(s) in scene".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_nrigid_nodes failed")
        return error_result("Failed to list nRigid nodes", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_nrigid_nodes`."""
    return list_nrigid_nodes(**kwargs)


if __name__ == "__main__":
    import json

    result = list_nrigid_nodes()
    print(json.dumps(result))
