"""Create a new namespace in Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def create_namespace(
    name: str,
    parent: str = ":",
    set_as_current: bool = False,
) -> dict:
    """Create a new namespace.

    Args:
        name: The namespace name to create (e.g. ``"char_hero"``).
        parent: Parent namespace path.  Use ``":"`` for root.  Default: ``":"``.
        set_as_current: If ``True``, set the new namespace as the current active
            namespace after creation.  Default: ``False``.

    Returns:
        ActionResultModel dict with ``namespace``, ``parent``, and ``full_path``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return error_result("Namespace name cannot be empty", "Provide a valid name").to_dict()

        previous = cmds.namespaceInfo(currentNamespace=True)
        cmds.namespace(setNamespace=parent)

        if cmds.namespace(exists=name):
            cmds.namespace(setNamespace=previous)
            return error_result(
                "Namespace already exists: {}".format(name),
                "Use rename_namespace or choose a different name",
            ).to_dict()

        cmds.namespace(add=name)
        full_path = "{}:{}".format(parent.rstrip(":"), name) if parent != ":" else ":{}".format(name)

        if set_as_current:
            cmds.namespace(setNamespace=full_path)
        else:
            cmds.namespace(setNamespace=previous)

        return success_result(
            "Created namespace '{}'".format(full_path),
            prompt="Use list_namespaces to verify or rename_namespace to adjust the name.",
            namespace=name,
            parent=parent,
            full_path=full_path,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_namespace failed")
        return error_result("Failed to create namespace", str(exc)).to_dict()


def main(**kwargs):
    return create_namespace(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_namespace("char_hero")))
