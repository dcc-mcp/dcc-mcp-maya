"""Bake nCloth simulation to a geometry cache."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def bake_cloth_cache(
    ncloth_shape: str,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
) -> dict:
    """Bake an nCloth simulation to disk as a geometry cache.

    Args:
        ncloth_shape: Name of the nCloth shape node to bake.
        start_frame: Simulation start frame. Defaults to timeline start.
        end_frame: Simulation end frame. Defaults to timeline end.

    Returns:
        ActionResultModel dict with ``context.start_frame``,
        ``context.end_frame``, and ``context.ncloth_shape``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, ncloth_shape)
        if err:
            return err

        if start_frame is None:
            start_frame = int(cmds.playbackOptions(query=True, minTime=True))
        if end_frame is None:
            end_frame = int(cmds.playbackOptions(query=True, maxTime=True))

        start_frame = int(start_frame)
        end_frame = int(end_frame)

        parents = cmds.listRelatives(ncloth_shape, parent=True, fullPath=False) or [ncloth_shape]
        mesh_transform = parents[0]
        cmds.select(mesh_transform)
        cmds.mel.eval('doCreateNclothCache 5 {{ "{}" }};'.format(ncloth_shape))

        return skill_success(
            "nCloth cache baked ({}-{})".format(start_frame, end_frame),
            prompt=(
                "Cloth cache baked for frames {}-{}. Playback is now deterministic without re-simulating.".format(
                    start_frame, end_frame
                )
            ),
            ncloth_shape=ncloth_shape,
            start_frame=start_frame,
            end_frame=end_frame,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake cloth cache")


@skill_entry
def main(**kwargs):
    return bake_cloth_cache(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
