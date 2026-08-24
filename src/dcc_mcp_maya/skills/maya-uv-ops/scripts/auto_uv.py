"""Generate and verify bounded automatic polygon UVs."""

from __future__ import annotations

import hashlib
import json

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._mutation import MayaUndoChunk
from dcc_mcp_maya.api import validate_node_exists


def _uv_state(cmds, object_name):
    # type: (...) -> dict
    current_sets = cmds.polyUVSet(object_name, query=True, currentUVSet=True) or []
    if len(current_sets) != 1 or not current_sets[0]:
        raise RuntimeError("Maya did not return one current UV set")
    uv_count = int(cmds.polyEvaluate(object_name, uvcoord=True) or 0)
    coordinates = cmds.polyEditUV("{}.map[*]".format(object_name), query=True) or []
    coordinates = [float(value) for value in coordinates]
    if uv_count > 0 and len(coordinates) < uv_count * 2:
        raise RuntimeError("Maya returned incomplete UV coordinate readback")
    payload = json.dumps(coordinates, separators=(",", ":"), allow_nan=False).encode("ascii")
    return {
        "uv_set": str(current_sets[0]),
        "uv_count": uv_count,
        "uv_digest": hashlib.sha256(payload).hexdigest(),
    }


def auto_uv(
    object_name,  # type: str
    planes=6,  # type: int
    percentage_space=0.2,  # type: float
):
    # type: (...) -> dict
    """Apply Maya automatic projection and require positive UV readback."""
    if isinstance(planes, bool) or not isinstance(planes, int) or planes not in (4, 5, 6, 8, 12):
        return skill_error("Invalid projection planes", "planes must be one of 4, 5, 6, 8, or 12")
    if (
        isinstance(percentage_space, bool)
        or not isinstance(percentage_space, (int, float))
        or not 0 <= percentage_space <= 5
    ):
        return skill_error("Invalid UV spacing", "percentage_space must be between 0 and 5")

    transaction = None
    before_state = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        before_state = _uv_state(cmds, object_name)
        transaction = MayaUndoChunk(cmds, "dcc_mcp_auto_uv")
        transaction.begin()
        cmds.polyAutoProjection(
            object_name,
            planes=planes,
            layout=2,
            scaleMode=1,
            optimize=1,
            percentageSpace=float(percentage_space),
            worldSpace=True,
            constructionHistory=False,
        )
        after_state = _uv_state(cmds, object_name)
        if after_state["uv_count"] <= 0 or after_state == before_state:
            receipt = transaction.rollback(lambda: _uv_state(cmds, object_name) == before_state)
            return skill_error(
                "Automatic UV verification failed",
                "Maya did not prove a new positive UV projection result",
                object_name=object_name,
                before_uv_count=before_state["uv_count"],
                uv_count=after_state["uv_count"],
                **receipt,
            )

        transaction.commit()
        return skill_success(
            "Generated and verified {} UV coordinates on '{}'".format(after_state["uv_count"], object_name),
            object_name=object_name,
            uv_set=after_state["uv_set"],
            uv_count=after_state["uv_count"],
            uv_digest=after_state["uv_digest"],
            changed=True,
            planes=planes,
            percentage_space=float(percentage_space),
            prompt="Use get_uv_info to inspect the result or assign_material to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        receipt = {}
        if transaction is not None and before_state is not None:
            receipt = transaction.rollback(lambda: _uv_state(cmds, object_name) == before_state)
        return skill_exception(exc, message="Failed to generate automatic UVs", **receipt)


@skill_entry
def main(**kwargs):
    # type: (...) -> dict
    """Entry point; delegates to :func:`auto_uv`."""
    return auto_uv(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
