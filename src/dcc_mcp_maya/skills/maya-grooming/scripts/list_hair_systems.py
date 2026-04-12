"""List all nHair systems in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_hair_systems() -> dict:
    """List all hairSystem nodes with follicle and nucleus info.

    Returns:
        ActionResultModel dict with ``context.hair_systems`` (list of dicts)
        and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        hair_systems = cmds.ls(type="hairSystem") or []
        result = []
        for hs in hair_systems:
            parents = cmds.listRelatives(hs, parent=True, fullPath=False) or [hs]
            transform = parents[0]

            follicles = cmds.listConnections(hs, type="follicle") or []
            nucleus_conn = cmds.listConnections(hs, type="nucleus") or []
            nucleus = nucleus_conn[0] if nucleus_conn else None

            stiffness = None
            if cmds.attributeQuery("stiffness", node=hs, exists=True):
                try:
                    stiffness = cmds.getAttr("{}.stiffness".format(hs))
                except Exception:
                    stiffness = None

            result.append(
                {
                    "hair_system": hs,
                    "transform": transform,
                    "follicle_count": len(follicles),
                    "nucleus": nucleus,
                    "stiffness": stiffness,
                }
            )

        return skill_success(
            "Found {} hair system(s)".format(len(result)),
            prompt="Use set_nhair_attribute to tune dynamics or add_nhair_cache to bake.",
            hair_systems=result,
            count=len(result),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list hair systems")


@skill_entry
def main(**kwargs):
    return list_hair_systems(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
