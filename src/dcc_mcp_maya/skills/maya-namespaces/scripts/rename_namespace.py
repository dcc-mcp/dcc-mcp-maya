"""Rename an existing Maya namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

# Built-in namespaces that must never be modified
_PROTECTED_NS = frozenset({"UI", "shared", ":"})


def rename_namespace(
    old_name: str,
    new_name: str,
) -> dict:
    """Rename an existing Maya namespace.

    Args:
        old_name: Current namespace name (without leading ``":"``).
        new_name: Desired new namespace name (without leading ``":"``).

    Returns:
        ActionResultModel dict with ``context.old_name``,
        ``context.new_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        old_ns = old_name.strip(":")
        new_ns = new_name.strip(":")

        if not old_ns:
            return error_result("Cannot rename root namespace", "old_name must not be empty or ':'").to_dict()

        if old_ns in _PROTECTED_NS:
            return error_result(
                "Cannot rename protected namespace: {}".format(old_ns),
                "Protected namespaces: {}".format(", ".join(sorted(_PROTECTED_NS))),
            ).to_dict()

        if not cmds.namespace(exists=":{}".format(old_ns)):
            return error_result(
                "Namespace does not exist: {}".format(old_ns),
                "Create the namespace first or check the name",
            ).to_dict()

        if cmds.namespace(exists=":{}".format(new_ns)):
            return error_result(
                "Namespace already exists: {}".format(new_ns),
                "Choose a different new_name",
            ).to_dict()

        cmds.namespace(rename=[":{}".format(old_ns), new_ns])

        return success_result(
            "Renamed namespace '{}' → '{}'".format(old_ns, new_ns),
            old_name=old_ns,
            new_name=new_ns,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("rename_namespace failed")
        return error_result("Failed to rename namespace '{}' to '{}'".format(old_name, new_name), str(exc)).to_dict()


def main(**kwargs):
    return rename_namespace(**kwargs)


if __name__ == "__main__":
    import json

    result = rename_namespace()
    print(json.dumps(result))
