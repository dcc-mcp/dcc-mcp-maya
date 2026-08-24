"""Generate and verify bounded automatic polygon UVs."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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
        uv_count = int(cmds.polyEvaluate(object_name, uvcoord=True) or 0)
        if uv_count <= 0:
            return skill_error(
                "Automatic UV verification failed",
                "Maya reported no UV coordinates after projection",
                object_name=object_name,
                uv_count=uv_count,
            )

        return skill_success(
            "Generated and verified {} UV coordinates on '{}'".format(uv_count, object_name),
            object_name=object_name,
            uv_count=uv_count,
            planes=planes,
            percentage_space=float(percentage_space),
            prompt="Use get_uv_info to inspect the result or assign_material to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to generate automatic UVs")


@skill_entry
def main(**kwargs):
    # type: (...) -> dict
    """Entry point; delegates to :func:`auto_uv`."""
    return auto_uv(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
