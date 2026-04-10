"""List all nParticle and nucleus nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_nparticle_systems() -> dict:
    """List all nParticle systems and nucleus solvers in the scene.

    Returns:
        ActionResultModel dict with particle systems and nucleus info.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        particle_shapes = cmds.ls(type="nParticle") or []
        nucleus_nodes = cmds.ls(type="nucleus") or []

        systems = []
        for shape in particle_shapes:
            info = {
                "shape": shape,
                "count": 0,
                "radius": None,
                "nucleus": None,
                "emitters": [],
            }  # type: dict

            try:
                info["count"] = cmds.nParticle(shape, q=True, count=True) or 0
            except Exception:
                pass

            try:
                if cmds.attributeQuery("radius", node=shape, exists=True):
                    info["radius"] = cmds.getAttr("{}.radius".format(shape))
            except Exception:
                pass

            try:
                nuc = cmds.listConnections(shape, type="nucleus") or []
                info["nucleus"] = nuc[0] if nuc else None
            except Exception:
                pass

            try:
                emitters = cmds.listConnections(shape, type="pointEmitter") or []
                info["emitters"] = list(set(emitters))
            except Exception:
                pass

            systems.append(info)

        nucleus_info = []
        for nuc in nucleus_nodes:
            ninfo = {"node": nuc, "gravity": None, "time_scale": None}  # type: dict
            try:
                ninfo["gravity"] = cmds.getAttr("{}.gravity".format(nuc))
                ninfo["time_scale"] = cmds.getAttr("{}.timeScale".format(nuc))
            except Exception:
                pass
            nucleus_info.append(ninfo)

        return success_result(
            "Found {} nParticle system(s) and {} nucleus solver(s)".format(
                len(systems), len(nucleus_nodes)
            ),
            prompt="Use set_nparticle_attribute to tune particle properties.",
            systems=systems,
            nucleus_solvers=nucleus_info,
            system_count=len(systems),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_nparticle_systems failed")
        return error_result("Failed to list nParticle systems", str(exc)).to_dict()


def main(**kwargs):
    return list_nparticle_systems(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_nparticle_systems()))
