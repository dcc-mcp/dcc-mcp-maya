"""Import a file into the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"i": True}  # type: dict
        if namespace:
            kwargs["namespace"] = namespace
        if merge_namespaces:
            kwargs["mergeNamespacesOnClash"] = True

        cmds.file(file_path, **kwargs)
        imported = cmds.ls(importedNodes=True) or []
        return skill_success(
            "Imported {} node(s) from {}".format(len(imported), file_path),
            file_path=file_path,
            imported_nodes=imported,
            count=len(imported),
            prompt="Check the result with list_render or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to import file: {}".format(file_path))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`import_file`."""
    return import_file(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
