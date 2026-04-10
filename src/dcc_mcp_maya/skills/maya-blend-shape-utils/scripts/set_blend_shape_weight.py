"""Set the weight of a specific blend shape target."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Union

logger = logging.getLogger(__name__)


def set_blend_shape_weight(
    blend_shape_node: str,
    target: Union[int, str],
    weight: float,
) -> dict:
    """Set the weight of a blend shape target.

    Args:
        blend_shape_node: Name of the blendShape node.
        target: Target index (int) or target alias name (str).
        weight: Weight value, typically in the range ``[0.0, 1.0]``.
            Values outside this range produce exaggerated shapes.

    Returns:
        ActionResultModel dict with ``context.blend_shape_node``,
        ``context.target_index``, and ``context.weight``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(blend_shape_node):
            return error_result(
                "Blend shape node not found: {}".format(blend_shape_node),
                "'{}' does not exist in the scene".format(blend_shape_node),
            ).to_dict()

        # Resolve target index
        if isinstance(target, str):
            aliases = cmds.aliasAttr(blend_shape_node, query=True) or []
            # aliasAttr returns [alias, attr, alias, attr ...]
            index = None
            for i in range(0, len(aliases), 2):
                if aliases[i] == target:
                    # attr looks like "weight[N]"
                    attr_name = aliases[i + 1]
                    try:
                        index = int(attr_name.split("[")[1].rstrip("]"))
                    except (IndexError, ValueError):
                        pass
                    break
            if index is None:
                return error_result(
                    "Target not found: {}".format(target),
                    "No alias '{}' on '{}'".format(target, blend_shape_node),
                ).to_dict()
        else:
            index = int(target)

        cmds.setAttr("{}.weight[{}]".format(blend_shape_node, index), weight)

        return success_result(
            "Set weight[{}] = {:.4f} on '{}'".format(index, weight, blend_shape_node),
            prompt="Use get_blend_shape_weights to verify, or set a keyframe with cmds.setKeyframe.",
            blend_shape_node=blend_shape_node,
            target_index=index,
            weight=weight,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_blend_shape_weight failed")
        return error_result("Failed to set blend shape weight", str(exc)).to_dict()


def main(**kwargs):
    return set_blend_shape_weight(**kwargs)


if __name__ == "__main__":
    import json

    result = set_blend_shape_weight("blendShape1", 0, 0.5)
    print(json.dumps(result, indent=2))
