"""Rename an existing Maya namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def rename_namespace(
    old_name: str,
    new_name: str,
) -> dict:
    """Rename a namespace.

    All objects within the namespace retain their membership; only the namespace
    identifier changes.

    Args:
        old_name: Current namespace name (relative, without leading ``:``)
            or full path (e.g. ``":char_hero"``).
        new_name: Target namespace name (relative).

    Returns:
        ActionResultModel dict with ``old_name``, ``new_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        old_rel = old_name.lstrip(":")
        new_rel = new_name.lstrip(":")

        _PROTECTED = {"UI", "shared"}
        if not old_rel:
            return error_result("Namespace name cannot be empty", "Provide a valid name").to_dict()
        if old_rel in _PROTECTED:
            return error_result(
                "Cannot rename protected namespace: {}".format(old_rel),
                "UI and shared are Maya built-in namespaces",
            ).to_dict()

        if not cmds.namespace(exists=":{}".format(old_rel)):
            return error_result(
                "Namespace not found: {}".format(old_name),
                "Verify the namespace with list_namespaces",
            ).to_dict()

        if cmds.namespace(exists=":{}".format(new_rel)):
            return error_result(
                "Namespace already exists: {}".format(new_name),
                "Choose a different name",
            ).to_dict()

        cmds.namespace(rename=[old_rel, new_rel])

        return success_result(
            "Renamed namespace '{}' -> '{}'".format(old_rel, new_rel),
            prompt="Use list_namespaces to verify the rename.",
            old_name=old_rel,
            new_name=new_rel,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("rename_namespace failed")
        return error_result("Failed to rename namespace", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`rename_namespace`."""
    return rename_namespace(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(rename_namespace("char_hero", "char_hero_v2")))
