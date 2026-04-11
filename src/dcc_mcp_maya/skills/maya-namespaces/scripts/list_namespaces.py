"""List all non-default namespaces with object counts."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

_DEFAULT_NAMESPACES = {"UI", "shared"}


def list_namespaces(include_defaults: bool = False) -> dict:
    """List all namespaces in the current scene.

    Args:
        include_defaults: If ``True``, include the built-in ``UI`` and ``shared``
            namespaces.  Default: ``False``.

    Returns:
        ActionResultModel dict with ``namespaces`` list.  Each entry contains
        ``name``, ``full_path``, and ``object_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        namespaces = []
        for ns in raw:
            base = ns.split(":")[-1]
            if not include_defaults and base in _DEFAULT_NAMESPACES:
                continue
            full_path = ns if ns.startswith(":") else ":{}".format(ns)
            # Count objects in namespace
            try:
                objects = cmds.ls("{}:*".format(ns.lstrip(":"))) or []
                obj_count = len(objects)
            except Exception:
                obj_count = 0

            namespaces.append(
                {
                    "name": base,
                    "full_path": full_path,
                    "object_count": obj_count,
                }
            )

        return success_result(
            "Found {} namespace(s)".format(len(namespaces)),
            prompt="Use rename_namespace or remove_namespace to manage them.",
            namespaces=namespaces,
            count=len(namespaces),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_namespaces failed")
        return error_result("Failed to list namespaces", str(exc)).to_dict()


def main(**kwargs):
    return list_namespaces(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_namespaces()))
