"""List all namespaces in the current scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_namespaces(root_only: bool = False) -> dict:
    """List all namespaces in the current scene.

    Args:
        root_only: If True, return only top-level namespaces directly under
            the root (``":"``).  If False (default), list all namespaces
            recursively.

    Returns:
        ActionResultModel dict with ``context.namespaces`` — a list of
        namespace strings — and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if root_only:
            raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=False) or []
        else:
            raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []

        # Filter built-in namespaces
        built_in = {"UI", "shared"}
        namespaces = [ns for ns in raw if ns not in built_in]

        return success_result(
            "Found {} namespace(s)".format(len(namespaces)),
            namespaces=namespaces,
            count=len(namespaces),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_namespaces failed")
        return error_result("Failed to list namespaces", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_namespaces`."""
    return list_namespaces(**kwargs)


if __name__ == "__main__":
    import json

    result = list_namespaces()
    print(json.dumps(result))
