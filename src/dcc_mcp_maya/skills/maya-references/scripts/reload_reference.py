"""Reload a previously unloaded (or modified) file reference."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def reload_reference(reference_node: str) -> dict:
    """Reload a previously unloaded (or modified) file reference.

    Args:
        reference_node: Name of the reference node to reload
            (e.g. ``"characterRN"``).  Use :func:`list_references` to
            discover reference nodes.

    Returns:
        ActionResultModel dict with ``context.reference_node``,
        ``context.file_path``, and ``context.loaded``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return error_result(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist".format(reference_node),
            ).to_dict()

        if cmds.objectType(reference_node) != "reference":
            return error_result(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}'".format(reference_node, cmds.objectType(reference_node)),
            ).to_dict()

        cmds.file(loadReference=reference_node)

        try:
            file_path = cmds.referenceQuery(reference_node, filename=True, withoutCopyNumber=True)
        except Exception:
            file_path = ""

        return success_result(
            "Reloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            file_path=file_path,
            loaded=True,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("reload_reference failed")
        return error_result("Failed to reload reference '{}'".format(reference_node), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`reload_reference`."""
    return reload_reference(**kwargs)


if __name__ == "__main__":
    import json

    result = reload_reference()
    print(json.dumps(result))
