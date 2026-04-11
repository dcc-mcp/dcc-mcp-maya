"""Bake an nHair simulation to a dynamic curve cache."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def add_nhair_cache(
    hair_system: str,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
) -> dict:
    """Bake an nHair system to a geometry cache (dynamic curves).

    Args:
        hair_system: Name of the hairSystem node to bake.
        start_frame: Simulation start frame. Defaults to timeline start.
        end_frame: Simulation end frame. Defaults to timeline end.

    Returns:
        ActionResultModel dict with ``context.hair_system``,
        ``context.start_frame``, and ``context.end_frame``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(hair_system):
            return error_result(
                "Node not found",
                "hairSystem '{}' does not exist".format(hair_system),
            ).to_dict()

        if start_frame is None:
            start_frame = int(cmds.playbackOptions(query=True, minTime=True))
        if end_frame is None:
            end_frame = int(cmds.playbackOptions(query=True, maxTime=True))

        start_frame = int(start_frame)
        end_frame = int(end_frame)

        cmds.select(hair_system)
        cmds.mel.eval('doCreateNclothCache 5 {{ "{}" }};'.format(hair_system))

        return success_result(
            "nHair cache baked ({}-{})".format(start_frame, end_frame),
            prompt=(
                "Hair cache baked for frames {}-{}. Playback is now deterministic without re-simulating.".format(
                    start_frame, end_frame
                )
            ),
            hair_system=hair_system,
            start_frame=start_frame,
            end_frame=end_frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_nhair_cache failed")
        return error_result("Failed to bake nHair cache", str(exc)).to_dict()


def main(**kwargs):
    return add_nhair_cache(**kwargs)


if __name__ == "__main__":
    import json

    result = add_nhair_cache("hairSystem1")
    print(json.dumps(result))
