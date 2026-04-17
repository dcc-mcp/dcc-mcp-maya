"""Maya texture baking and color management actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes

logger = logging.getLogger(__name__)


def bake_textures(
    objects: List[str],
    file_path: str,
    resolution: int = 512,
    bake_type: str = "diffuse",
    renderer: str = "mentalRay",
    overscan: int = 3,
) -> dict:
    """Bake lighting or texture to a UV map.

    Args:
        objects: List of mesh objects to bake.
        file_path: Output texture file path (without extension).
        resolution: Output texture resolution in pixels.  Default: 512.
        bake_type: Bake type — ``"diffuse"``, ``"full_render"``,
            ``"normals"``, ``"ao"``.  Default: ``"diffuse"``.
        renderer: Renderer to use for baking — ``"mentalRay"`` or
            ``"arnold"``.  Default: ``"mentalRay"``.
        overscan: Anti-alias overscan in pixels.  Default: 3.

    Returns:
        ToolResult dict with ``context.baked_objects`` and
        ``context.file_path``.
    """

    valid_types = ("diffuse", "full_render", "normals", "ao")
    if bake_type not in valid_types:
        return skill_error(
            "Invalid bake_type: {}".format(bake_type),
            "Use one of: {}".format(", ".join(valid_types)),
        )

    valid_renderers = ("mentalRay", "arnold")
    if renderer not in valid_renderers:
        return skill_error(
            "Invalid renderer: {}".format(renderer),
            "Use one of: {}".format(", ".join(valid_renderers)),
        )

    if not objects:
        return skill_error("No objects specified for baking")

    if resolution < 1:
        return skill_error(
            "Invalid resolution: {}".format(resolution),
            "Resolution must be >= 1",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, list(objects))
        if err:
            return err

        bake_type_map = {
            "diffuse": "diffuse",
            "full_render": "fullRender",
            "normals": "normals",
            "ao": "occlusion",
        }
        internal_type = bake_type_map[bake_type]

        # Use Maya's convertSolidTx / bakeTextures for flexibility
        cmds.select(objects, replace=True)
        baked_files = []
        for obj in objects:
            out_path = "{}_{}".format(file_path, obj.replace("|", "_").replace(":", "_"))
            try:
                cmds.convertSolidTx(
                    obj,
                    fileImageName=out_path,
                    resolutionX=resolution,
                    resolutionY=resolution,
                    antiAlias=True,
                    bm=0,  # blend mode: normal
                    fts=True,  # fill texture seams
                    sp=False,  # do not show progress
                    backgroundMode=0,
                    renderSampler=internal_type,
                )
                baked_files.append(out_path)
            except Exception as bake_exc:
                logger.warning("Bake skipped for '%s': %s", obj, bake_exc)

        return skill_success(
            "Baked {} object(s) to '{}'".format(len(baked_files), file_path),
            objects=objects,
            baked_count=len(baked_files),
            file_path=file_path,
            resolution=resolution,
            bake_type=bake_type,
            renderer=renderer,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake textures")


def set_color_management(
    enabled: bool = True,
    input_color_space: Optional[str] = None,
    rendering_space: Optional[str] = None,
    output_transform: Optional[str] = None,
) -> dict:
    """Configure scene color management (OCIO / Maya native).

    Args:
        enabled: Enable or disable color management globally.  Default: True.
        input_color_space: Input color space name (e.g. ``"sRGB"``,
            ``"ACEScg"``).  If None, leaves the current setting unchanged.
        rendering_space: Rendering/working color space (e.g. ``"scene-linear
            Rec 709/sRGB"``).  If None, leaves unchanged.
        output_transform: Output view transform name (e.g.
            ``"sRGB gamma"``).  If None, leaves unchanged.

    Returns:
        ToolResult dict with current color management configuration.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Toggle color management
        cmds.colorManagementPrefs(edit=True, cmEnabled=enabled)

        if input_color_space:
            try:
                cmds.colorManagementPrefs(edit=True, inputColorSpace=input_color_space)
            except Exception as exc:
                logger.warning("Could not set inputColorSpace '%s': %s", input_color_space, exc)

        if rendering_space:
            try:
                cmds.colorManagementPrefs(edit=True, renderingSpaceName=rendering_space)
            except Exception as exc:
                logger.warning("Could not set renderingSpace '%s': %s", rendering_space, exc)

        if output_transform:
            try:
                cmds.colorManagementPrefs(edit=True, outputTransformName=output_transform)
            except Exception as exc:
                logger.warning("Could not set outputTransform '%s': %s", output_transform, exc)

        # Query resulting state
        try:
            cm_enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        except Exception:
            cm_enabled = enabled

        try:
            current_rendering = cmds.colorManagementPrefs(query=True, renderingSpaceName=True)
        except Exception:
            current_rendering = rendering_space

        try:
            current_output = cmds.colorManagementPrefs(query=True, outputTransformName=True)
        except Exception:
            current_output = output_transform

        return skill_success(
            "Color management {}".format("enabled" if enabled else "disabled"),
            enabled=cm_enabled,
            rendering_space=current_rendering,
            output_transform=current_output,
            input_color_space=input_color_space,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set color management")


def list_color_spaces() -> dict:
    """List all available color spaces registered in Maya's color management.

    Returns:
        ToolResult dict with ``context.color_spaces`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        try:
            spaces = cmds.colorManagementPrefs(query=True, inputColorSpaceNames=True) or []
        except Exception:
            spaces = []

        try:
            rendering_spaces = cmds.colorManagementPrefs(query=True, renderingSpaceNames=True) or []
        except Exception:
            rendering_spaces = []

        try:
            output_transforms = cmds.colorManagementPrefs(query=True, outputTransformNames=True) or []
        except Exception:
            output_transforms = []

        try:
            cm_enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        except Exception:
            cm_enabled = False

        return skill_success(
            "Color space list retrieved",
            color_management_enabled=cm_enabled,
            input_color_spaces=list(spaces),
            rendering_spaces=list(rendering_spaces),
            output_transforms=list(output_transforms),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list color spaces")
