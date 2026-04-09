"""Import a file into the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def import_file(
    file_path: str,
    namespace: Optional[str] = None,
    merge_namespaces: bool = False,
) -> dict:
    """Import a file into the current Maya scene.

    Supports any format Maya recognises (FBX, OBJ, Alembic, Maya ASCII/Binary,
    etc.).

    Args:
        file_path: Absolute path to the file to import.
        namespace: Optional namespace to assign to imported nodes.
        merge_namespaces: If True, merge with existing namespaces.

    Returns:
        ActionResultModel dict with ``context.imported_nodes`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"i": True}  # type: dict
        if namespace:
            kwargs["namespace"] = namespace
        if merge_namespaces:
            kwargs["mergeNamespacesOnClash"] = True

        cmds.file(file_path, **kwargs)
        imported = cmds.ls(importedNodes=True) or []
        return success_result(
            "Imported {} node(s) from {}".format(len(imported), file_path),
            file_path=file_path,
            imported_nodes=imported,
            count=len(imported),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("import_file failed")
        return error_result("Failed to import file: {}".format(file_path), str(exc)).to_dict()


def main(**kwargs):
    return import_file(**kwargs)


if __name__ == "__main__":
    import json

    result = import_file()
    print(json.dumps(result))
