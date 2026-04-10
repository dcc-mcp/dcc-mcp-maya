"""Import an Alembic (.abc) file into the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def import_alembic(
    file_path: str,
    namespace: Optional[str] = None,
    fit_time_range: bool = False,
) -> dict:
    """Import an Alembic archive into the current scene.

    Args:
        file_path: Path to the ``.abc`` file.
        namespace: Optional namespace prefix for imported nodes.
        fit_time_range: If ``True``, set the timeline range to match the cache.

    Returns:
        ActionResultModel dict with ``context.file_path`` and ``context.namespace``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not file_path:
        return error_result("No file path specified", "Provide a valid .abc file path.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Load AbcImport plugin if needed
        if not cmds.pluginInfo("AbcImport", query=True, loaded=True):
            cmds.loadPlugin("AbcImport")

        import_kwargs = {}
        if namespace:
            import_kwargs["namespace"] = namespace
        if fit_time_range:
            import_kwargs["fitTimeRange"] = True

        cmds.AbcImport(file_path, **import_kwargs)

        return success_result(
            "Imported Alembic from '{}'".format(file_path),
            prompt="Alembic imported. Use get_scene_info to inspect the imported objects.",
            file_path=file_path,
            namespace=namespace or "",
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("import_alembic failed")
        return error_result("Failed to import Alembic", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return import_alembic(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(import_alembic("/tmp/test.abc")))
