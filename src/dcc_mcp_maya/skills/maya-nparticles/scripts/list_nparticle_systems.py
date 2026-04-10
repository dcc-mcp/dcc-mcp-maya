"""List all nParticle systems in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_nparticle_systems() -> dict:
    """List all nParticle objects in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.particles`` (list of dicts with
        node name, nucleus, and particle count) and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        particle_nodes = cmds.ls(type="nParticle") or []
        items = []
        for node in particle_nodes:
            info = {"node": node}
            # Attempt to find connected nucleus
            connections = cmds.listConnections(node, type="nucleus") or []
            info["nucleus"] = connections[0] if connections else None
            try:
                info["particle_count"] = cmds.getParticleAttr(node, attribute="count") or 0
            except Exception:
                info["particle_count"] = 0
            items.append(info)

        return success_result(
            "Found {} nParticle system(s)".format(len(items)),
            prompt="Use set_nparticle_attribute to modify particle properties.",
            particles=items,
            count=len(items),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_nparticle_systems failed")
        return error_result("Failed to list nParticle systems", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_nparticle_systems(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_nparticle_systems()))
