"""Enable or disable an Arnold AOV by name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def enable_aov(name: str, enabled: bool = True) -> dict:
    """Enable or disable an Arnold AOV.

    Args:
        name: The AOV name as stored in ``aiAOV.name``.
        enabled: ``True`` to enable, ``False`` to disable.  Default: True.

    Returns:
        ActionResultModel dict with ``context.aov_node``, ``context.enabled``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return skill_error("AOV name is required", "Provide a non-empty AOV name")

        nodes = cmds.ls(type="aiAOV") or []
        target_node = None
        for node in nodes:
            try:
                if cmds.getAttr("{}.name".format(node)) == name:
                    target_node = node
                    break
            except Exception:
                pass

        if target_node is None:
            return skill_error(
                "AOV '{}' not found".format(name),
                "No aiAOV node with name '{}' exists in the scene".format(name),
            )

        cmds.setAttr("{}.enabled".format(target_node), enabled)
        state_label = "enabled" if enabled else "disabled"
        return skill_success(
            "Arnold AOV '{}' {}".format(name, state_label),
            prompt="Use list_aovs to verify the AOV state.",
            aov_node=target_node,
            aov_name=name,
            enabled=enabled,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set AOV state for '{}'".format(name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`enable_aov`."""
    return enable_aov(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
