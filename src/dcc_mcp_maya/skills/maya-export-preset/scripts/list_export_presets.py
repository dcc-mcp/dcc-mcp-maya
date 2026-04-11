"""List all available Maya export presets in a directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_export_presets(preset_dir: Optional[str] = None) -> dict:
    """List all ``.json`` export preset files in a directory.

    Args:
        preset_dir: Directory to scan. Defaults to
            ``<project_root>/export_presets``.

    Returns:
        ActionResultModel dict with ``context.presets`` (list of dicts)
        and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not preset_dir:
            project = cmds.workspace(query=True, rootDirectory=True)
            preset_dir = os.path.join(project, "export_presets")

        if not os.path.isdir(preset_dir):
            return skill_success(
                "No export presets directory found",
                prompt="Use save_export_preset to create your first preset.",
                presets=[],
                count=0,
                preset_dir=preset_dir,
            )

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

        return skill_success(
            "Found {} export preset(s)".format(len(presets)),
            prompt="Use load_export_preset with the preset path to restore settings.",
            presets=presets,
            count=len(presets),
            preset_dir=preset_dir,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list export presets")


@skill_entry
def main(**kwargs):
    return list_export_presets(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
