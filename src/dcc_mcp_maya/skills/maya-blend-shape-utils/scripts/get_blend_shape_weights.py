"""Query all target names and weights for a blend shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def get_blend_shape_weights(blend_shape_node: str) -> dict:
    """Get the weight of every target on a blend shape node.

    Args:
        blend_shape_node: Name of the blendShape node to inspect.

    Returns:
        ActionResultModel dict with ``context.targets`` (list of dicts with
        ``index``, ``name``, and ``weight`` keys) and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(blend_shape_node):
            return maya_error(
                "Blend shape node not found: {}".format(blend_shape_node),
                "'{}' does not exist in the scene".format(blend_shape_node),
            )

        weights = cmds.blendShape(blend_shape_node, query=True, weight=True) or []

        # Build an index → alias mapping from aliasAttr
        aliases_flat = cmds.aliasAttr(blend_shape_node, query=True) or []
        index_to_name = {}
        for i in range(0, len(aliases_flat), 2):
            alias = aliases_flat[i]
            attr = aliases_flat[i + 1]  # e.g. "weight[3]"
            try:
                idx = int(attr.split("[")[1].rstrip("]"))
                index_to_name[idx] = alias
            except (IndexError, ValueError):
                pass

        targets = []
        for idx, w in enumerate(weights):
            targets.append(
                {
                    "index": idx,
                    "name": index_to_name.get(idx, "target_{}".format(idx)),
                    "weight": w,
                }
            )

        return maya_success(
            "Queried {} target(s) on '{}'".format(len(targets), blend_shape_node),
            prompt="Use set_blend_shape_weight to modify any target's value.",
            blend_shape_node=blend_shape_node,
            targets=targets,
            count=len(targets),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get blend shape weights")


def main(**kwargs):
    return get_blend_shape_weights(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(get_blend_shape_weights("blendShape1"), indent=2))
