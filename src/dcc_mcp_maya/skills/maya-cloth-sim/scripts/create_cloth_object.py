"""Convert a mesh to an nCloth object."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

_PRESETS = {
    "denim": {"thickness": 0.02, "stretchResistance": 100.0, "bendResistance": 0.5, "mass": 1.0},
    "silk": {"thickness": 0.005, "stretchResistance": 50.0, "bendResistance": 0.05, "mass": 0.3},
    "rubber": {"thickness": 0.1, "stretchResistance": 20.0, "bendResistance": 5.0, "mass": 2.0},
    "default": {},
}


def run(params: dict) -> object:
    """Convert a mesh to nCloth.

    Args:
        params: Dictionary with keys:
            - mesh (str): Transform node of the mesh to convert.
            - preset (str): Cloth preset name: "denim", "silk", "rubber", "default". Default "default".
            - thickness (float): Override collision thickness. Optional.
            - mass (float): Override cloth mass. Optional.

    Returns:
        ActionResultModel with nCloth node name.
    """
    mesh = params.get("mesh", "")
    preset_name = params.get("preset", "default")
    thickness = params.get("thickness", None)
    mass = params.get("mass", None)

    if not mesh:
        return error_result("Invalid parameter", "mesh must not be empty.")

    try:
        if not cmds.objExists(mesh):
            return error_result("Mesh not found", "'{0}' does not exist.".format(mesh))

        cmds.select(mesh, replace=True)
        result = cmds.nCloth()
        cloth_node = result[0] if result else ""

        preset = _PRESETS.get(preset_name, {})
        if thickness is not None:
            preset["thickness"] = thickness
        if mass is not None:
            preset["mass"] = mass

        for attr, value in preset.items():
            if cmds.attributeQuery(attr, node=cloth_node, exists=True):
                cmds.setAttr("{0}.{1}".format(cloth_node, attr), value)

        return success_result(
            "Created nCloth from mesh '{0}' with preset '{1}'".format(mesh, preset_name),
            prompt=(
                "nCloth created. Use add_cloth_collider to add collision objects, "
                "then simulate_cloth to run the simulation."
            ),
            cloth_node=cloth_node,
            mesh=mesh,
            preset=preset_name,
        )
    except Exception as exc:
        return error_result("Failed to create cloth object", str(exc))
