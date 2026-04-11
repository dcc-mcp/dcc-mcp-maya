"""List all instancer nodes and their linked particle systems and geometry."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_instancers() -> dict:
    """List all particle instancer nodes in the scene.

    Returns:
        ActionResultModel dict with ``context.instancers`` (list of dicts with
        ``node``, ``particle_system``, and ``instance_objects`` keys) and
        ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nodes = cmds.ls(type="instancer") or []
        results = []
        for node in nodes:
            # Find connected particle system (inputPoints plug)
            particle_conns = cmds.listConnections("{}.inputPoints".format(node), source=True, destination=False) or []
            particle_system = particle_conns[0] if particle_conns else ""

            # Instance geometry is connected via inputHierarchy
            geo_conns = cmds.listConnections("{}.inputHierarchy".format(node), source=True, destination=False) or []

            results.append(
                {
                    "node": node,
                    "particle_system": particle_system,
                    "instance_objects": geo_conns,
                }
            )

        return maya_success(
            "Found {} instancer node(s)".format(len(results)),
            prompt="Use add_instance_object to add geometry, or set_instancer_attribute to drive per-particle variation.",
            instancers=results,
            count=len(results),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list instancers")


def main(**kwargs):
    return list_instancers(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_instancers(), indent=2))
