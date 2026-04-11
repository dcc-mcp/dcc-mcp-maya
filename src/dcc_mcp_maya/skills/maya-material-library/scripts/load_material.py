"""Recreate a material from a JSON preset and optionally assign it to objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def load_material(
    file_path: str,
    material_name: Optional[str] = None,
    assign_to: Optional[List[str]] = None,
) -> dict:
    """Recreate a material from a JSON preset file.

    Args:
        file_path: Path to the ``.json`` preset file created by ``save_material``.
        material_name: Override node name for the created material.  Defaults to
            the ``material`` field stored in the preset.
        assign_to: Optional list of mesh / transform nodes to assign the
            recreated material to.

    Returns:
        ActionResultModel dict with the created node name and assignment info.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        try:
            with open(file_path) as fh:
                preset_data = json.load(fh)
        except (IOError, ValueError) as exc:
            return maya_error("Cannot read preset '{}'".format(file_path), str(exc))

        node_type = preset_data.get("node_type", "lambert")
        default_name = preset_data.get("material", "mat_preset")
        name = material_name or default_name

        # Create node
        mat_node = cmds.shadingNode(node_type, asShader=True, name=name)

        # Apply attributes
        attrs = preset_data.get("attributes", {})
        applied = []
        for attr, val in attrs.items():
            full = "{}.{}".format(mat_node, attr)
            try:
                if isinstance(val, list):
                    cmds.setAttr(full, *val, type="double3")
                else:
                    cmds.setAttr(full, val)
                applied.append(attr)
            except Exception:
                pass

        # Optionally assign to meshes
        assigned_to = []
        if assign_to:
            sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}_SG".format(mat_node))
            cmds.connectAttr("{}.outColor".format(mat_node), "{}.surfaceShader".format(sg), force=True)
            for obj in assign_to:
                if cmds.objExists(obj):
                    cmds.sets(obj, edit=True, forceElement=sg)
                    assigned_to.append(obj)

        return maya_success(
            "Loaded material '{}' from '{}'".format(mat_node, file_path),
            prompt="Use assign_material to assign this material to additional objects.",
            material=mat_node,
            node_type=node_type,
            applied_attributes=len(applied),
            assigned_to=assigned_to,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to load material preset")


def main(**kwargs):
    return load_material(**kwargs)


if __name__ == "__main__":
    import json as _json

    print(_json.dumps(load_material("/tmp/mat_lib/lambert1.json")))
