"""Query the current color management configuration."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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

        return maya_success(
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
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get color management info")


def main(**kwargs):
    return get_color_management_info(**kwargs)


if __name__ == "__main__":
    import json

    result = get_color_management_info()
    print(json.dumps(result))
