"""List all material preset files in a library directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_materials(library_dir: str) -> dict:
    """List all material preset JSON files in a library directory.

    Args:
        library_dir: Directory to search for ``.json`` preset files.

    Returns:
        ActionResultModel dict with a list of preset info dicts.
    """
    try:
        if not os.path.isdir(library_dir):
            return skill_error(
                "Library directory not found: '{}'".format(library_dir),
                "Create the directory or run save_material first",
            )

        presets = []
        for fname in sorted(os.listdir(library_dir)):
            if not fname.endswith(".json"):
                continue
            full_path = os.path.join(library_dir, fname)
            info = {
                "name": os.path.splitext(fname)[0],
                "file_path": full_path,
                "node_type": "unknown",
            }
            try:
                with open(full_path) as fh:
                    data = json.load(fh)
                info["node_type"] = data.get("node_type", "unknown")
                info["attribute_count"] = len(data.get("attributes", {}))
            except Exception:
                pass
            presets.append(info)

        return skill_success(
            "Found {} material preset(s) in '{}'".format(len(presets), library_dir),
            prompt="Use load_material with a file_path to apply a preset.",
            presets=presets,
            count=len(presets),
            library_dir=library_dir,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list material presets")


@skill_entry
def main(**kwargs):
    return list_materials(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
