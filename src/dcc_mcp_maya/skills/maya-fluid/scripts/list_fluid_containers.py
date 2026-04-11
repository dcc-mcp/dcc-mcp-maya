"""List all fluid containers in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def list_fluid_containers() -> dict:
    """List all fluidShape nodes with their transform parents.

    Returns:
        ActionResultModel dict with ``context.containers`` (list of dicts)
        and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        fluid_shapes = cmds.ls(type="fluidShape") or []
        containers = []
        for shape in fluid_shapes:
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or [shape]
            transform = parents[0]
            resolution = None
            if cmds.attributeQuery("resolution", node=shape, exists=True):
                raw = cmds.getAttr("{}.resolution".format(shape))
                resolution = list(raw[0]) if raw else None
            containers.append(
                {
                    "transform": transform,
                    "shape": shape,
                    "resolution": resolution,
                }
            )

        return maya_success(
            "Found {} fluid container(s)".format(len(containers)),
            prompt="Use set_fluid_attribute to adjust simulation parameters.",
            containers=containers,
            count=len(containers),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list fluid containers")

def main(**kwargs):
    return list_fluid_containers(**kwargs)

if __name__ == "__main__":
    import json

    result = list_fluid_containers()
    print(json.dumps(result))
