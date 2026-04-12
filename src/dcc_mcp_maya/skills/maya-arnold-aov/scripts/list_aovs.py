"""List all Arnold AOVs currently defined in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_INT_TO_TYPE = {1: "FLOAT", 2: "INT", 3: "RGB", 4: "RGBA", 5: "VECTOR"}


def list_aovs() -> dict:
    """List all Arnold AOV nodes (``aiAOV``) in the current scene.

    Returns:
        ActionResultModel dict with ``context.aovs`` (list of dicts with
        ``name``, ``type``, ``enabled``, ``node``) and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # When mtoa is absent aiAOV nodes cannot exist; return empty list gracefully
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            return skill_success(
                "Arnold (mtoa) plugin is not loaded — no AOVs available",
                prompt="Load the mtoa plugin then use add_aov to create Arnold AOVs.",
                aovs=[],
                count=0,
            )

        nodes = cmds.ls(type="aiAOV") or []
        aovs = []
        for node in nodes:
            try:
                aov_name = cmds.getAttr("{}.name".format(node))
                type_int = cmds.getAttr("{}.type".format(node))
                enabled = bool(cmds.getAttr("{}.enabled".format(node)))
                aovs.append(
                    {
                        "node": node,
                        "name": aov_name,
                        "type": _INT_TO_TYPE.get(type_int, "RGB"),
                        "enabled": enabled,
                    }
                )
            except Exception:
                pass

        return skill_success(
            "Found {} Arnold AOV(s)".format(len(aovs)),
            prompt="Use add_aov to create more passes or enable_aov to toggle individual AOVs.",
            aovs=aovs,
            count=len(aovs),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list AOVs")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_aovs`."""
    return list_aovs(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
