"""Configure Maya OCIO color management for rendering."""

from __future__ import annotations

from pathlib import Path

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_MAX_COLOR_NAMES = 512
_MAX_COLOR_NAME_LENGTH = 256


def _bounded_names(values, label: str):
    names = sorted({str(value) for value in (values or []) if str(value)})
    if len(names) > _MAX_COLOR_NAMES:
        raise ValueError("{} returned more than {} entries".format(label, _MAX_COLOR_NAMES))
    if any(len(name) > _MAX_COLOR_NAME_LENGTH for name in names):
        raise ValueError("{} returned an overlong entry".format(label))
    return names


@skill_entry
def main(
    config_file_path: str,
    rendering_space_name: str = "ACEScg",
    display_name: str = "Rec.1886 Rec.709 - Display",
    view_name: str = "ACES 1.0 - SDR Video",
    apply_output_transform: bool = True,
    **kwargs,
) -> dict:
    """Apply an OCIO config and one render/display/view contract."""
    config_path = Path(config_file_path).expanduser()
    if config_path.suffix.lower() != ".ocio" or not config_path.is_file():
        return skill_error(
            "Invalid OCIO config",
            "config_file_path must point to an existing .ocio file",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        config_path = config_path.resolve()
        cmds.colorManagementPrefs(edit=True, cmEnabled=True)
        cmds.colorManagementPrefs(edit=True, configFilePath=str(config_path))
        cmds.colorManagementPrefs(edit=True, cmConfigFileEnabled=True)
        cmds.colorManagementPrefs(refresh=True)
        cmds.colorManagementPrefs(edit=True, renderingSpaceName=rendering_space_name)
        cmds.colorManagementPrefs(edit=True, displayName=display_name)
        cmds.colorManagementPrefs(edit=True, viewName=view_name)
        cmds.colorManagementPrefs(
            edit=True,
            outputTarget="renderer",
            outputUseViewTransform=True,
            outputTransformEnabled=apply_output_transform,
        )

        state = {
            "config_file_path": cmds.colorManagementPrefs(query=True, configFilePath=True),
            "rendering_space_name": cmds.colorManagementPrefs(query=True, renderingSpaceName=True),
            "display_name": cmds.colorManagementPrefs(query=True, displayName=True),
            "view_name": cmds.colorManagementPrefs(query=True, viewName=True),
            "ocio_v2_enabled": bool(cmds.colorManagementPrefs(query=True, ociov2Enabled=True)),
            "output_transform_enabled": bool(
                cmds.colorManagementPrefs(
                    query=True,
                    outputTarget="renderer",
                    outputTransformEnabled=True,
                )
            ),
            "input_color_spaces": _bounded_names(
                cmds.colorManagementPrefs(query=True, inputColorSpaceNames=True),
                "input color spaces",
            ),
            "rendering_spaces": _bounded_names(
                cmds.colorManagementPrefs(query=True, renderingSpaceNames=True),
                "rendering spaces",
            ),
            "output_transforms": _bounded_names(
                cmds.colorManagementPrefs(query=True, outputTransformNames=True),
                "output transforms",
            ),
        }
        expected = {
            "config_file_path": str(config_path),
            "rendering_space_name": rendering_space_name,
            "display_name": display_name,
            "view_name": view_name,
            "output_transform_enabled": apply_output_transform,
        }
        mismatches = {
            key: {"expected": value, "actual": state[key]} for key, value in expected.items() if state[key] != value
        }
        if mismatches:
            return skill_error(
                "Maya OCIO settings did not match the request",
                "Use display and view names exposed by the selected OCIO config",
                mismatches=mismatches,
                **state,
            )
        return skill_success(
            "Configured Maya OCIO color management",
            prompt="Assign explicit input color spaces to file textures before rendering.",
            **state,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to configure Maya OCIO color management")


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
