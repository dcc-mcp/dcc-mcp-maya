"""List all Maya Fluid containers in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_fluid_containers() -> dict:
    """List all Maya Fluid Effects containers in the scene.

    Returns:
        ActionResultModel dict with ``context.containers`` list and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        fluid_shapes = cmds.ls(type="fluidShape") or []

        result = []
        for shape in fluid_shapes:
            info = {"shape": shape}
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            info["transform"] = parents[0] if parents else None

            # Resolution
            try:
                res_x = cmds.getAttr("{}.resolutionX".format(shape))
                res_y = cmds.getAttr("{}.resolutionY".format(shape))
                res_z = cmds.getAttr("{}.resolutionZ".format(shape))
                info["resolution"] = [res_x, res_y, res_z]
            except Exception:
                info["resolution"] = None

            # Connected emitters
            emitters = cmds.listConnections(shape, type="fluidEmitter") or []
            info["emitters"] = list(set(emitters))

            result.append(info)

        return success_result(
            "Found {} fluid container(s)".format(len(result)),
            prompt=(
                "Use add_fluid_emitter to attach emitters, or set_fluid_attribute to tune parameters."
                if result
                else "No fluid containers found. Use create_fluid_container to add one."
            ),
            containers=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_fluid_containers failed")
        return error_result("Failed to list fluid containers", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_fluid_containers(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_fluid_containers()))
