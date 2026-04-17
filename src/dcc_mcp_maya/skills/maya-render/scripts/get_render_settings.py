"""Get current Maya render settings."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_FORMAT_NAMES = {
    0: "gif",
    1: "soft",
    2: "rla",
    3: "tiff",
    5: "sgi",
    8: "jpg",
    9: "eps",
    10: "iff",
    13: "maya16iff",
    19: "tga",
    20: "bmp",
    32: "png",
    40: "exr",
}


def get_render_settings() -> dict:
    """Return the current Maya render settings.

    Returns:
        ToolResult dict with ``context.width``, ``context.height``,
        ``context.renderer``, ``context.start_frame``, ``context.end_frame``,
        ``context.image_format``, and ``context.output_path``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")
        start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
        end_frame = cmds.getAttr("defaultRenderGlobals.endFrame")
        renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        fmt_code = cmds.getAttr("defaultRenderGlobals.imageFormat")
        image_format = _FORMAT_NAMES.get(fmt_code, str(fmt_code))
        output_path = cmds.getAttr("defaultRenderGlobals.imageFilePrefix") or ""

        return skill_success(
            "Render settings: {}×{} | {} | frames {}-{} | format {}".format(
                width, height, renderer, int(start_frame), int(end_frame), image_format
            ),
            prompt="Use set_render_settings to update any of these values.",
            width=width,
            height=height,
            renderer=renderer,
            start_frame=start_frame,
            end_frame=end_frame,
            image_format=image_format,
            output_path=output_path,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get render settings")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_render_settings`."""
    return get_render_settings(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
