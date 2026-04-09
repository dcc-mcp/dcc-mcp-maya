"""Query a summary of the current scene render configuration."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Scene render stats: {} @ {}x{}".format(renderer, width, height),
            renderer=renderer,
            width=width,
            height=height,
            start_frame=start_frame,
            end_frame=end_frame,
            output_file_prefix=output_prefix,
            quality=quality,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_scene_render_stats failed")
        return error_result("Failed to query scene render stats", str(exc)).to_dict()


def main(**kwargs):
    return get_scene_render_stats(**kwargs)


if __name__ == "__main__":
    import json

    result = get_scene_render_stats()
    print(json.dumps(result))
