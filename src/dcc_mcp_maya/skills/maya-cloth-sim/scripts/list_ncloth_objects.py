"""List all nCloth objects in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_ncloth_objects() -> dict:
    """List all nCloth shape nodes with mesh and nucleus connections.

    Returns:
        ActionResultModel dict with ``context.cloth_objects`` (list of dicts),
        ``context.nucleus_nodes``, and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ncloth_shapes = cmds.ls(type="nCloth") or []
        cloth_objects = []
        for shape in ncloth_shapes:
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or [shape]
            transform = parents[0]

            nucleus_conn = cmds.listConnections(shape, type="nucleus") or []
            nucleus = nucleus_conn[0] if nucleus_conn else None

            input_mesh = None
            input_conns = cmds.listConnections("{}.inputMesh".format(shape), source=True, destination=False) or []
            if input_conns:
                input_mesh = input_conns[0]

            cloth_objects.append(
                {
                    "shape": shape,
                    "transform": transform,
                    "input_mesh": input_mesh,
                    "nucleus": nucleus,
                }
            )

        nucleus_nodes = cmds.ls(type="nucleus") or []

        return maya_success(
            "Found {} nCloth object(s)".format(len(cloth_objects)),
            prompt="Use set_ncloth_attribute or bake_cloth_cache to modify cloth behavior.",
            cloth_objects=cloth_objects,
            nucleus_nodes=nucleus_nodes,
            count=len(cloth_objects),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list nCloth objects")


def main(**kwargs):
    return list_ncloth_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = list_ncloth_objects()
    print(json.dumps(result))
