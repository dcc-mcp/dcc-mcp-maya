"""Get the value of an attribute on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, validate_node_exists


def get_attribute(node_name: str, attribute: str) -> dict:
    """Get the value of an attribute on a Maya node.

    Args:
        node_name: Name of the Maya node.
        attribute: Attribute name (e.g. ``"translateX"``, ``"visibility"``).

    Returns:
        ActionResultModel dict with ``context.value``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node_name)
        if err:
            return err

        full_attr = "{}.{}".format(node_name, attribute)
        if not cmds.objExists(full_attr):
            return maya_error(
                "Attribute not found: {}".format(full_attr),
                "'{}.{}' does not exist on this node".format(node_name, attribute),
            )

        raw = cmds.getAttr(full_attr)
        # Flatten single-element tuples returned for compound attrs
        if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], tuple):
            value = list(raw[0])
        else:
            value = raw

        return maya_success(
            "{}.{} = {}".format(node_name, attribute, value),
            prompt="Use set_attribute to change the value.",
            node_name=node_name,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get attribute")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_attribute`."""
    return get_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = get_attribute("pSphere1", "translateX")
    print(json.dumps(result))
