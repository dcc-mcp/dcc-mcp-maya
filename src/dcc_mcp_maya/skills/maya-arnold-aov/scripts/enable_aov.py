"""Enable or disable an Arnold AOV by name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def enable_aov(name: str, enabled: bool = True) -> dict:
    """Enable or disable an Arnold AOV.

    Args:
        name: The AOV name as stored in ``aiAOV.name``.
        enabled: ``True`` to enable, ``False`` to disable.  Default: True.

    Returns:
        ActionResultModel dict with ``context.aov_node``, ``context.enabled``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return error_result("AOV name is required", "Provide a non-empty AOV name").to_dict()

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
            return error_result(
                "AOV '{}' not found".format(name),
                "No aiAOV node with name '{}' exists in the scene".format(name),
            ).to_dict()

        cmds.setAttr("{}.enabled".format(target_node), enabled)
        state_label = "enabled" if enabled else "disabled"
        return success_result(
            "Arnold AOV '{}' {}".format(name, state_label),
            prompt="Use list_aovs to verify the AOV state.",
            aov_node=target_node,
            aov_name=name,
            enabled=enabled,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("enable_aov failed")
        return error_result("Failed to set AOV state for '{}'".format(name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`enable_aov`."""
    return enable_aov(**kwargs)


if __name__ == "__main__":
    import json

    result = enable_aov("diffuse", True)
    print(json.dumps(result))
