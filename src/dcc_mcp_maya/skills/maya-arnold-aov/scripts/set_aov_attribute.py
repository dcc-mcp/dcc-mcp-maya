"""Set an attribute on an Arnold AOV node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_aov_attribute(name: str, attribute: str, value: object) -> dict:
    """Set a named attribute on the Arnold AOV node identified by *name*.

    Args:
        name: The AOV name as stored in ``aiAOV.name`` (not the Maya node
            name).
        attribute: Attribute name on the ``aiAOV`` node (e.g. ``"type"``,
            ``"enabled"``, ``"lightGroups"``).
        value: New attribute value.  Strings are set with ``type="string"``;
            booleans and numbers are set directly.

    Returns:
        ActionResultModel dict with ``context.aov_node``, ``context.attribute``,
        ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return error_result("AOV name is required", "Provide a non-empty AOV name").to_dict()
        if not attribute:
            return error_result("Attribute name is required", "Provide a non-empty attribute name").to_dict()

        # Find the aiAOV node
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
                "No aiAOV node with name '{}' exists".format(name),
            ).to_dict()

        attr_path = "{}.{}".format(target_node, attribute)
        if not cmds.objExists(attr_path):
            return error_result(
                "Attribute '{}' not found on AOV node".format(attribute),
                "The attribute '{}' does not exist on '{}'".format(attribute, target_node),
            ).to_dict()

        if isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(name, attribute, value),
            prompt="Use list_aovs to review all AOV settings.",
            aov_node=target_node,
            aov_name=name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_aov_attribute failed")
        return error_result("Failed to set AOV attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_aov_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_aov_attribute("diffuse", "enabled", True)
    print(json.dumps(result))
