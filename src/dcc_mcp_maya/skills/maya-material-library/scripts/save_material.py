"""Serialize a material and its attributes to a JSON preset file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

# Attributes to skip during serialization (read-only / computed)
_SKIP_ATTRS = {"message", "caching", "frozen", "isHistoricallyInteresting", "nodeState",
               "binMembership", "hyperLayout", "identification"}


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material):
            return error_result(
                "Material '{}' not found".format(material),
                "Use list_shaders or list_materials_in_scene to find material names",
            ).to_dict()

        node_type = cmds.objectType(material)
        preset = preset_name or material
        file_path = os.path.join(library_dir, "{}.json".format(preset))

        os.makedirs(library_dir, exist_ok=True)
        if not overwrite and os.path.exists(file_path):
            return error_result(
                "Preset '{}' already exists".format(file_path),
                "Set overwrite=True to replace it",
            ).to_dict()

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

        return success_result(
            "Saved material '{}' preset to '{}'".format(material, file_path),
            prompt="Use load_material to apply this preset in another scene.",
            file_path=file_path,
            node_type=node_type,
            attribute_count=len(data),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("save_material failed")
        return error_result("Failed to save material preset", str(exc)).to_dict()


def main(**kwargs):
    return save_material(**kwargs)


if __name__ == "__main__":
    import json as _json

    print(_json.dumps(save_material("lambert1", "/tmp/mat_lib")))
