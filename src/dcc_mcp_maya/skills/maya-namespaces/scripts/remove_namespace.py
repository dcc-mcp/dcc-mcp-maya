"""Remove a namespace and merge its contents into the parent namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def remove_namespace(
    name: str,
    force: bool = False,
) -> dict:
    """Remove a namespace, merging its objects into the parent.

    When ``force`` is ``True`` the namespace is removed even if it contains
    objects (they are reparented to the parent namespace).  When ``False``,
    an error is returned if the namespace is not empty.

    Args:
        name: Namespace to remove (relative or full path).
        force: Move objects to parent namespace before removal.  Default: ``False``.

    Returns:
        ActionResultModel dict with ``namespace`` and ``merged_objects``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        rel = name.lstrip(":")
        if not cmds.namespace(exists=rel):
            return error_result(
                "Namespace not found: {}".format(name),
                "Verify the namespace with list_namespaces",
            ).to_dict()

        objects_in_ns = cmds.ls("{}:*".format(rel)) or []

        if objects_in_ns and not force:
            return error_result(
                "Namespace '{}' is not empty ({} objects)".format(rel, len(objects_in_ns)),
                "Set force=True to merge objects into the parent namespace",
            ).to_dict()

        if objects_in_ns and force:
            cmds.namespace(moveNamespace=[rel, ":"], force=True)

        cmds.namespace(removeNamespace=rel)

        return success_result(
            "Removed namespace '{}' ({} objects merged)".format(rel, len(objects_in_ns)),
            prompt="Use list_namespaces to confirm removal.",
            namespace=rel,
            merged_objects=len(objects_in_ns),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_namespace failed")
        return error_result("Failed to remove namespace", str(exc)).to_dict()


def main(**kwargs):
    return remove_namespace(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(remove_namespace("char_hero", force=True)))
