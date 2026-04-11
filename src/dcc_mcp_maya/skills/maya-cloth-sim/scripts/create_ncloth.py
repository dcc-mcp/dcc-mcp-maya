"""Create an nCloth simulation on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_ncloth(
    mesh: str,
    nucleus: Optional[str] = None,
    preset: str = "cotton",
) -> dict:
    """Convert a polygon mesh into an nCloth simulation object.

    Args:
        mesh: Name of the polygon mesh transform to convert.
        nucleus: Optional existing nucleus node name to use.
        preset: Cloth preset name: ``'cotton'``, ``'silk'``, ``'denim'``, or
            ``'rubber'``. Default ``'cotton'``.

    Returns:
        ActionResultModel dict with ``context.ncloth_shape`` and
        ``context.nucleus``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        cmds.select(mesh)
        cmds.nClothCreate()

        ncloth_shapes = cmds.ls(type="nCloth") or []
        ncloth_shape = ncloth_shapes[-1] if ncloth_shapes else ""

        nucleus_nodes = cmds.ls(type="nucleus") or []
        nucleus_node = (
            nucleus if (nucleus and cmds.objExists(nucleus)) else (nucleus_nodes[-1] if nucleus_nodes else "")
        )

        presets = {
            "cotton": {"stretchResistance": 50.0, "bendResistance": 0.4},
            "silk": {"stretchResistance": 30.0, "bendResistance": 0.1},
            "denim": {"stretchResistance": 80.0, "bendResistance": 2.0},
            "rubber": {"stretchResistance": 10.0, "bendResistance": 0.05},
        }
        if ncloth_shape and preset in presets:
            for attr, val in presets[preset].items():
                try:
                    cmds.setAttr("{}.{}".format(ncloth_shape, attr), val)
                except Exception:
                    pass

        return skill_success(
            "nCloth created on '{}'".format(mesh),
            prompt=(
                "nCloth '{}' created with '{}' preset. "
                "Use set_ncloth_attribute to fine-tune, then bake_cloth_cache to record.".format(ncloth_shape, preset)
            ),
            ncloth_shape=ncloth_shape,
            nucleus=nucleus_node,
            preset=preset,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create nCloth")


@skill_entry
def main(**kwargs):
    return create_ncloth(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
