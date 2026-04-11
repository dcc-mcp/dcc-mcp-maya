"""Set an attribute on an Arnold AOV node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return maya_error("AOV name is required", "Provide a non-empty AOV name")
        if not attribute:
            return maya_error("Attribute name is required", "Provide a non-empty attribute name")

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
            return maya_error(
                "AOV '{}' not found".format(name),
                "No aiAOV node with name '{}' exists".format(name),
            )

        attr_path = "{}.{}".format(target_node, attribute)
        if not cmds.objExists(attr_path):
            return maya_error(
                "Attribute '{}' not found on AOV node".format(attribute),
                "The attribute '{}' does not exist on '{}'".format(attribute, target_node),
            )

        if isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        else:
            cmds.setAttr(attr_path, value)

        return maya_success(
            "Set {}.{} = {}".format(name, attribute, value),
            prompt="Use list_aovs to review all AOV settings.",
            aov_node=target_node,
            aov_name=name,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set AOV attribute")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_aov_attribute`."""
    return set_aov_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_aov_attribute("diffuse", "enabled", True)
    print(json.dumps(result))
