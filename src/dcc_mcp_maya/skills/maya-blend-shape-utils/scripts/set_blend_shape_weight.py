"""Set the weight of a specific blend shape target."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Union

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(blend_shape_node):
            return skill_error(
                "Blend shape node not found: {}".format(blend_shape_node),
                "'{}' does not exist in the scene".format(blend_shape_node),
            )

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
                return skill_error(
                    "Target not found: {}".format(target),
                    "No alias '{}' on '{}'".format(target, blend_shape_node),
                )
        else:
            index = int(target)

        cmds.setAttr("{}.weight[{}]".format(blend_shape_node, index), weight)

        return skill_success(
            "Set weight[{}] = {:.4f} on '{}'".format(index, weight, blend_shape_node),
            prompt="Use get_blend_shape_weights to verify, or set a keyframe with cmds.setKeyframe.",
            blend_shape_node=blend_shape_node,
            target_index=index,
            weight=weight,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set blend shape weight")


@skill_entry
def main(**kwargs):
    return set_blend_shape_weight(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
