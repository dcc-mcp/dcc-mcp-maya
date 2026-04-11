"""List all render pass elements in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_render_passes() -> dict:
    """List all render pass elements (renderPass and aiAOV nodes) in the scene.

    Returns:
        ActionResultModel dict with ``context.passes`` (list of dicts with
        ``name``, ``type``, ``enabled``) and ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        passes = []

        for node_type in ("renderPass", "aiAOV"):
            nodes = cmds.ls(type=node_type) or []
            for node in nodes:
                info = {"name": node, "type": node_type, "enabled": True}
                if cmds.attributeQuery("renderable", node=node, exists=True):
                    info["enabled"] = bool(cmds.getAttr("{}.renderable".format(node)))
                if cmds.attributeQuery("name", node=node, exists=True):
                    try:
                        info["aov_name"] = cmds.getAttr("{}.name".format(node))
                    except Exception:
                        pass
                passes.append(info)

        return skill_success(
            "Found {} render pass(es) in the scene".format(len(passes)),
            prompt="Use enable_render_pass to toggle or set_render_pass_output to configure paths.",
            passes=passes,
            count=len(passes),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list render passes")


@skill_entry
def main(**kwargs):
    return list_render_passes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
