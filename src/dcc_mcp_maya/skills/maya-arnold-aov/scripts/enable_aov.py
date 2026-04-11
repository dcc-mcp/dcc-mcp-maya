"""Enable or disable an Arnold AOV by name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
            return maya_error("AOV name is required", "Provide a non-empty AOV name")

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
            return maya_error(
                "AOV '{}' not found".format(name),
                "No aiAOV node with name '{}' exists in the scene".format(name),
            )

        cmds.setAttr("{}.enabled".format(target_node), enabled)
        state_label = "enabled" if enabled else "disabled"
        return maya_success(
            "Arnold AOV '{}' {}".format(name, state_label),
            prompt="Use list_aovs to verify the AOV state.",
            aov_node=target_node,
            aov_name=name,
            enabled=enabled,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set AOV state for '{}'".format(name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`enable_aov`."""
    return enable_aov(**kwargs)


if __name__ == "__main__":
    import json

    result = enable_aov("diffuse", True)
    print(json.dumps(result))
