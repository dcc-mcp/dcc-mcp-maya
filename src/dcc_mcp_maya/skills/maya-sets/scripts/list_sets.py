"""List all Maya object sets in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_sets(include_internal: bool = False) -> dict:
    """List all Maya object sets in the scene.

    Args:
        include_internal: If False (default), built-in Maya sets such as
            ``"defaultCreaseDataSet"`` or ``"defaultLightSet"`` are excluded.

    Returns:
        ActionResultModel dict with ``context.sets`` — a list of dicts with
        ``name`` and ``member_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    # Maya built-in default sets that clutter the result when include_internal=False
    _INTERNAL_SETS = frozenset(
        [
            "defaultCreaseDataSet",
            "defaultLightSet",
            "defaultObjectSet",
            "initialParticleSE",
            "initialShadingGroup",
        ]
    )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        all_sets = cmds.ls(type="objectSet") or []
        result = []
        for set_node in all_sets:
            if not include_internal and set_node in _INTERNAL_SETS:
                continue
            members = cmds.sets(set_node, query=True) or []
            result.append(
                {
                    "name": set_node,
                    "member_count": len(members),
                }
            )

        return success_result(
            "Found {} object set(s)".format(len(result)),
            sets=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_sets failed")
        return error_result("Failed to list object sets", str(exc)).to_dict()


def main(**kwargs):
    return list_sets(**kwargs)


if __name__ == "__main__":
    import json

    result = list_sets()
    print(json.dumps(result))
