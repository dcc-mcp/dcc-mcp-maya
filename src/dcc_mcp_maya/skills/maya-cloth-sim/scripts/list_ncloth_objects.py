"""List all nCloth objects in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_ncloth_objects() -> dict:
    """List all nCloth shape nodes with mesh and nucleus connections.

    Returns:
        ToolResult dict with ``context.cloth_objects`` (list of dicts),
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

        return skill_success(
            "Found {} nCloth object(s)".format(len(cloth_objects)),
            prompt="Use set_ncloth_attribute or bake_cloth_cache to modify cloth behavior.",
            cloth_objects=cloth_objects,
            nucleus_nodes=nucleus_nodes,
            count=len(cloth_objects),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list nCloth objects")


@skill_entry
def main(**kwargs):
    return list_ncloth_objects(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
