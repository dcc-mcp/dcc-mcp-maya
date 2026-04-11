"""List all available Maya export presets in a directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def list_export_presets(preset_dir: Optional[str] = None) -> dict:
    """List all ``.json`` export preset files in a directory.

    Args:
        preset_dir: Directory to scan. Defaults to
            ``<project_root>/export_presets``.

    Returns:
        ActionResultModel dict with ``context.presets`` (list of dicts)
        and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not preset_dir:
            project = cmds.workspace(query=True, rootDirectory=True)
            preset_dir = os.path.join(project, "export_presets")

        if not os.path.isdir(preset_dir):
            return success_result(
                "No export presets directory found",
                prompt="Use save_export_preset to create your first preset.",
                presets=[],
                count=0,
                preset_dir=preset_dir,
            ).to_dict()

        presets = []
        for fname in sorted(os.listdir(preset_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(preset_dir, fname)
            try:
                with open(fpath, "r") as fh:
                    data = json.load(fh)
                presets.append(
                    {
                        "preset_name": data.get("preset_name", fname[:-5]),
                        "format": data.get("format", ""),
                        "frame_range": data.get("frame_range"),
                        "path": fpath,
                    }
                )
            except Exception:
                presets.append(
                    {
                        "path": fpath,
                        "preset_name": fname[:-5],
                        "error": "invalid JSON",
                    }
                )

        return success_result(
            "Found {} export preset(s)".format(len(presets)),
            prompt="Use load_export_preset with the preset path to restore settings.",
            presets=presets,
            count=len(presets),
            preset_dir=preset_dir,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_export_presets failed")
        return error_result("Failed to list export presets", str(exc)).to_dict()


def main(**kwargs):
    return list_export_presets(**kwargs)


if __name__ == "__main__":
    import json as _json

    result = list_export_presets()
    print(_json.dumps(result))
