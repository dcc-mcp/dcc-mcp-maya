"""Create an nHair system on a polygon mesh surface."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Node not found",
                "Mesh '{}' does not exist".format(mesh),
            ).to_dict()

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

        return success_result(
            "nHair system created on '{}'".format(mesh),
            prompt=(
                "Hair system '{}' created with {} follicles. Use set_nhair_attribute to adjust dynamics.".format(
                    hair_system, follicle_count
                )
            ),
            hair_system=hair_system,
            follicle_count=follicle_count,
            mesh=mesh,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_nhair_system failed")
        return error_result("Failed to create nHair system", str(exc)).to_dict()


def main(**kwargs):
    return create_nhair_system(**kwargs)


if __name__ == "__main__":
    import json

    result = create_nhair_system("pSphere1")
    print(json.dumps(result))
