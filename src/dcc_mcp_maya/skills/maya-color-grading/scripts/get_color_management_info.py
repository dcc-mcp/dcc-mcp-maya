"""Query the current color management configuration."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_color_management_info() -> dict:
    """Query Maya's active color management configuration.

    Returns the current rendering space, view transform, output transform,
    and whether OCIO / native color management is enabled.

    Returns:
        ActionResultModel dict with ``context.enabled``, ``context.rendering_space``,
        ``context.view_transform``, ``context.output_transform``,
        ``context.ocio_config_path``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        rendering_space = cmds.colorManagementPrefs(query=True, renderingSpaceName=True) or ""
        view_transform = cmds.colorManagementPrefs(query=True, viewTransformName=True) or ""
        output_transform = ""
        try:
            output_transform = cmds.colorManagementPrefs(query=True, outputTransformName=True) or ""
        except Exception:
            pass
        ocio_config = ""
        try:
            ocio_config = cmds.colorManagementPrefs(query=True, configFilePath=True) or ""
        except Exception:
            pass

        return skill_success(
            "Color management: {} (rendering='{}', view='{}')".format(
                "enabled" if enabled else "disabled",
                rendering_space,
                view_transform,
            ),
            prompt="Use set_rendering_space or set_view_transform to modify the color pipeline.",
            enabled=enabled,
            rendering_space=rendering_space,
            view_transform=view_transform,
            output_transform=output_transform,
            ocio_config_path=ocio_config,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get color management info")


@skill_entry
def main(**kwargs):
    return get_color_management_info(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
