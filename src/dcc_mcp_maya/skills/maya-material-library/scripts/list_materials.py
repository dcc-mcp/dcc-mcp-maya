"""List all material preset files in a library directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_materials(library_dir: str) -> dict:
    """List all material preset JSON files in a library directory.

    Args:
        library_dir: Directory to search for ``.json`` preset files.

    Returns:
        ActionResultModel dict with a list of preset info dicts.
    """
    try:
        if not os.path.isdir(library_dir):
            return maya_error(
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

        return maya_success(
            "Found {} material preset(s) in '{}'".format(len(presets), library_dir),
            prompt="Use load_material with a file_path to apply a preset.",
            presets=presets,
            count=len(presets),
            library_dir=library_dir,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list material presets")


def main(**kwargs):
    return list_materials(**kwargs)


if __name__ == "__main__":
    import json as _json

    print(_json.dumps(list_materials("/tmp/mat_lib")))
