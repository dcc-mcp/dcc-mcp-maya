"""Create an nHair system on a polygon mesh surface."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_nhair_system(
    mesh: str,
    uv_density: int = 3,
    hair_length: float = 5.0,
) -> dict:
    """Create an nHair follicle system on a polygon mesh.

    Args:
        mesh: Name of the polygon mesh to attach hair to.
        uv_density: Number of follicles per UV direction. Default ``3``.
        hair_length: Approximate hair length in scene units. Default ``5.0``.

    Returns:
        ActionResultModel dict with ``context.hair_system`` and
        ``context.follicle_count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        cmds.select(mesh)
        cmds.mel.eval("assignNewHairSystem;makeHairCurves 0 {0} {0} 0 0 0 0 0 0 0 1 1;".format(uv_density))

        hair_systems = cmds.ls(type="hairSystem") or []
        hair_system = hair_systems[-1] if hair_systems else ""

        follicles = cmds.ls(type="follicle") or []
        follicle_count = len(follicles)

        if hair_system and hair_length != 5.0:
            try:
                cmds.setAttr("{}.hairLength".format(hair_system), hair_length)
            except Exception:
                pass

        return skill_success(
            "nHair system created on '{}'".format(mesh),
            prompt=(
                "Hair system '{}' created with {} follicles. Use set_nhair_attribute to adjust dynamics.".format(
                    hair_system, follicle_count
                )
            ),
            hair_system=hair_system,
            follicle_count=follicle_count,
            mesh=mesh,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create nHair system")


@skill_entry
def main(**kwargs):
    return create_nhair_system(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
