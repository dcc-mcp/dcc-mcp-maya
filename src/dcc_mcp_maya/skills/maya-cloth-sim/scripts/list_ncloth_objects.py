"""List all nCloth objects in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_ncloth_objects() -> dict:
    """List all nCloth shape nodes with mesh and nucleus connections.

    Returns:
        ActionResultModel dict with ``context.cloth_objects`` (list of dicts),
        ``context.nucleus_nodes``, and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} nCloth object(s)".format(len(cloth_objects)),
            prompt="Use set_ncloth_attribute or bake_cloth_cache to modify cloth behavior.",
            cloth_objects=cloth_objects,
            nucleus_nodes=nucleus_nodes,
            count=len(cloth_objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_ncloth_objects failed")
        return error_result("Failed to list nCloth objects", str(exc)).to_dict()


def main(**kwargs):
    return list_ncloth_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = list_ncloth_objects()
    print(json.dumps(result))
