"""Query a summary of the current scene render configuration."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_scene_render_stats() -> dict:
    """Query a summary of the current scene render configuration.

    Gathers renderer, resolution, frame range, output path prefix and
    the current render quality attributes from ``defaultRenderQuality``.

    Returns:
        ActionResultModel dict with:
        - ``context.renderer`` — current renderer string
        - ``context.width`` / ``context.height`` — render resolution
        - ``context.start_frame`` / ``context.end_frame``
        - ``context.output_file_prefix``
        - ``context.quality`` — dict of quality attribute values
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer") or "unknown"
        width = int(cmds.getAttr("defaultResolution.width"))
        height = int(cmds.getAttr("defaultResolution.height"))
        start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
        end_frame = cmds.getAttr("defaultRenderGlobals.endFrame")
        output_prefix = cmds.getAttr("defaultRenderGlobals.imageFilePrefix") or ""

        quality = {}
        rq_node = "defaultRenderQuality"
        for attr_name in (
            "edgeAntiAliasing",
            "shadingSamples",
            "maxShadingSamples",
            "visibilitySamples",
            "maxVisibilitySamples",
            "shadingRayDepth",
            "reflectionRayDepth",
            "refractionRayDepth",
        ):
            plug = "{}.{}".format(rq_node, attr_name)
            if cmds.objExists(plug):
                quality[attr_name] = cmds.getAttr(plug)

        return skill_success(
            "Scene render stats: {} @ {}x{}".format(renderer, width, height),
            renderer=renderer,
            width=width,
            height=height,
            start_frame=start_frame,
            end_frame=end_frame,
            output_file_prefix=output_prefix,
            quality=quality,
            prompt="Check the result with list_render or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to query scene render stats")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_scene_render_stats`."""
    return get_scene_render_stats(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
