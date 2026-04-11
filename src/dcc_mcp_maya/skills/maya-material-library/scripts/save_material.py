"""Serialize a material and its attributes to a JSON preset file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Attributes to skip during serialization (read-only / computed)
_SKIP_ATTRS = {
    "message",
    "caching",
    "frozen",
    "isHistoricallyInteresting",
    "nodeState",
    "binMembership",
    "hyperLayout",
    "identification",
}


def save_material(
    material: str,
    library_dir: str,
    preset_name: Optional[str] = None,
    attributes: Optional[List[str]] = None,
    overwrite: bool = True,
) -> dict:
    """Serialize a material node and its scalar attributes to a JSON preset.

    Args:
        material: Name of the Maya shading node to serialize.
        library_dir: Directory where the preset ``.json`` file is saved.
        preset_name: File name stem (without ``.json``).  Defaults to the
            material node name.
        attributes: Explicit list of attributes to capture.  If None, all
            numeric/string settable attributes are captured automatically.
        overwrite: If False and the preset file already exists, return an
            error.  Default: True.

    Returns:
        ActionResultModel dict with ``context.file_path`` and attribute count.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material):
            return maya_error(
                "Material '{}' not found".format(material),
                "Use list_shaders or list_materials_in_scene to find material names",
            )

        node_type = cmds.objectType(material)
        preset = preset_name or material
        file_path = os.path.join(library_dir, "{}.json".format(preset))

        os.makedirs(library_dir, exist_ok=True)
        if not overwrite and os.path.exists(file_path):
            return maya_error(
                "Preset '{}' already exists".format(file_path),
                "Set overwrite=True to replace it",
            )

        # Collect attributes
        if attributes:
            attrs_to_save = attributes
        else:
            attrs_to_save = cmds.listAttr(material, scalar=True, settable=True) or []
            attrs_to_save = [a for a in attrs_to_save if a not in _SKIP_ATTRS and "." not in a]

        data = {}  # type: dict
        for attr in attrs_to_save:
            full = "{}.{}".format(material, attr)
            try:
                val = cmds.getAttr(full)
                # Flatten single-element lists
                if isinstance(val, list) and len(val) == 1:
                    val = val[0]
                # Convert tuples to lists for JSON serialisation
                if isinstance(val, tuple):
                    val = list(val)
                data[attr] = val
            except Exception:
                pass

        preset_data = {
            "node_type": node_type,
            "material": material,
            "attributes": data,
        }

        with open(file_path, "w") as fh:
            json.dump(preset_data, fh, indent=2)

        return maya_success(
            "Saved material '{}' preset to '{}'".format(material, file_path),
            prompt="Use load_material to apply this preset in another scene.",
            file_path=file_path,
            node_type=node_type,
            attribute_count=len(data),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to save material preset")


def main(**kwargs):
    return save_material(**kwargs)


if __name__ == "__main__":
    import json as _json

    print(_json.dumps(save_material("lambert1", "/tmp/mat_lib")))
