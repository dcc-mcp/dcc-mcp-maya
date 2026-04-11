"""Query all target names and weights for a blend shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, blend_shape_node)
        if err:
            return err

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

        return skill_success(
            "Queried {} target(s) on '{}'".format(len(targets), blend_shape_node),
            prompt="Use set_blend_shape_weight to modify any target's value.",
            blend_shape_node=blend_shape_node,
            targets=targets,
            count=len(targets),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get blend shape weights")


@skill_entry
def main(**kwargs):
    return get_blend_shape_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
