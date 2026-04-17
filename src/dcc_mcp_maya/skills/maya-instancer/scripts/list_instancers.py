"""List all instancer nodes and their linked particle systems and geometry."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_instancers() -> dict:
    """List all particle instancer nodes in the scene.

    Returns:
        ToolResult dict with ``context.instancers`` (list of dicts with
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

        return skill_success(
            "Found {} instancer node(s)".format(len(results)),
            prompt="Use add_instance_object to add geometry, or set_instancer_attribute to drive per-particle variation.",
            instancers=results,
            count=len(results),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list instancers")


@skill_entry
def main(**kwargs):
    return list_instancers(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
