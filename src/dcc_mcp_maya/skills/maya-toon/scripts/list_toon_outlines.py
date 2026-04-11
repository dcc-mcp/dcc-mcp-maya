"""List all pfxToon nodes in the scene with their linked meshes."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


def list_toon_outlines() -> dict:
    """List all pfxToon outline nodes and their linked meshes.

    Returns:
        ActionResultModel dict with a list of toon outline info dicts.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        toon_nodes = cmds.ls(type="pfxToon") or []
        result = []
        for node in toon_nodes:
            info = {"node": node, "meshes": [], "line_width": None}  # type: dict
            try:
                info["line_width"] = cmds.getAttr("{}.lineWidth".format(node))
            except Exception:
                pass

            # Find connected meshes via displaySurface compound array
            try:
                connections = cmds.listConnections(node, source=True, destination=False, type="mesh") or []
                info["meshes"] = list(set(connections))
            except Exception:
                pass

            result.append(info)

        return skill_success(
            "Found {} pfxToon outline(s)".format(len(result)),
            prompt="Use set_outline_width to adjust width or add_toon_outline to add new outlines.",
            outlines=result,
            count=len(result),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list toon outlines")


@skill_entry
def main(**kwargs):
    return list_toon_outlines(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
