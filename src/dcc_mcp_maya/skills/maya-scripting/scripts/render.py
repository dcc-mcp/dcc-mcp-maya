"""Maya render and viewport capture actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import base64
import os
import tempfile
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_render_settings(
    width: int = 1920,
    height: int = 1080,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    renderer: Optional[str] = None,
) -> dict:
    """Set the render globals (resolution, frame range, renderer).

    Args:
        width: Render width in pixels.  Default: 1920.
        height: Render height in pixels.  Default: 1080.
        start_frame: Start frame for batch rendering.  If None, left unchanged.
        end_frame: End frame for batch rendering.  If None, left unchanged.
        renderer: Renderer name (e.g. ``"arnold"``, ``"vray"``, ``"mayaSoftware"``).
            If None, left unchanged.

    Returns:
        ActionResultModel dict with applied render settings.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)
        cmds.setAttr("defaultResolution.deviceAspectRatio", float(width) / float(height))

        applied = {"width": width, "height": height}

        if start_frame is not None:
            cmds.setAttr("defaultRenderGlobals.startFrame", start_frame)
            applied["start_frame"] = start_frame
        if end_frame is not None:
            cmds.setAttr("defaultRenderGlobals.endFrame", end_frame)
            applied["end_frame"] = end_frame
        if renderer is not None:
            cmds.setAttr("defaultRenderGlobals.currentRenderer", renderer, type="string")
            applied["renderer"] = renderer

        return maya_success(
            "Render settings applied ({}x{})".format(width, height),
            **applied,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set render settings")


def capture_viewport(
    width: int = 1920,
    height: int = 1080,
    frame: Optional[float] = None,
) -> dict:
    """Capture the Maya viewport as a PNG image (base64-encoded).

    Uses ``cmds.playblast`` to render the active viewport into a temporary
    PNG file and returns the image bytes as a Base64 string.

    Args:
        width: Image width in pixels.  Default: 1920.
        height: Image height in pixels.  Default: 1080.
        frame: Frame to capture.  Defaults to the current frame.

    Returns:
        ActionResultModel dict with ``context.image`` (base64 PNG string).
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if frame is None:
            frame = cmds.currentTime(query=True)

        # playblast writes  <prefix>.<frame_padded>.png
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Remove the .png suffix for playblast prefix
        prefix = tmp_path[:-4]
        cmds.playblast(
            frame=[frame],
            format="image",
            compression="png",
            filename=prefix,
            width=width,
            height=height,
            percent=100,
            viewer=False,
            showOrnaments=False,
        )

        # playblast appends .<frame>.png
        padded = "{}.{}.png".format(prefix, str(int(frame)).zfill(4))
        img_path = padded if os.path.exists(padded) else prefix + ".png"

        with open(img_path, "rb") as fh:
            img_bytes = fh.read()
        os.unlink(img_path)

        encoded = base64.b64encode(img_bytes).decode("ascii")
        return maya_success(
            "Viewport captured ({}x{} @ frame {})".format(width, height, frame),
            image=encoded,
            width=width,
            height=height,
            frame=frame,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to capture viewport")


def import_file(
    file_path: str,
    namespace: Optional[str] = None,
    merge_namespaces: bool = False,
) -> dict:
    """Import a file into the current Maya scene.

    Supports any format Maya recognises (FBX, OBJ, Alembic, Maya ASCII/Binary,
    etc.).

    Args:
        file_path: Absolute path to the file to import.
        namespace: Optional namespace to assign to imported nodes.
        merge_namespaces: If True, merge with existing namespaces.

    Returns:
        ActionResultModel dict with ``context.imported_nodes`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"i": True}  # type: dict
        if namespace:
            kwargs["namespace"] = namespace
        if merge_namespaces:
            kwargs["mergeNamespacesOnClash"] = True

        cmds.file(file_path, **kwargs)
        imported = cmds.ls(importedNodes=True) or []
        return maya_success(
            "Imported {} node(s) from {}".format(len(imported), file_path),
            file_path=file_path,
            imported_nodes=imported,
            count=len(imported),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to import file: {}".format(file_path))


def export_selection(
    file_path: str,
    file_type: str = "FBX export",
) -> dict:
    """Export the current selection to a file.

    Args:
        file_path: Destination file path.
        file_type: Export format string as understood by ``cmds.file(type=...)``.
            Common values: ``"FBX export"``, ``"OBJexport"``, ``"mayaBinary"``,
            ``"mayaAscii"``, ``"Alembic"``.  Default: ``"FBX export"``.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        saved = cmds.file(
            file_path,
            exportSelected=True,
            type=file_type,
            force=True,
        )
        return maya_success(
            "Selection exported to {}".format(saved),
            file_path=saved,
            file_type=file_type,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to export selection")


# Render quality preset mappings
# Keys map to (globalQuality, shadingQuality, raytracingQuality) tuples
# used by defaultRenderQuality node attrs: shadingSamples, maxShadingSamples,
# visibilitySamples, etc.
_RENDER_QUALITY_PRESETS = {
    "low": {
        "edgeAntiAliasing": 0,  # Lowest preset
        "shadingSamples": 1,
        "maxShadingSamples": 1,
        "visibilitySamples": 1,
        "maxVisibilitySamples": 1,
        "shadingRayDepth": 1,
        "reflectionRayDepth": 1,
        "refractionRayDepth": 1,
    },
    "medium": {
        "edgeAntiAliasing": 2,
        "shadingSamples": 2,
        "maxShadingSamples": 4,
        "visibilitySamples": 1,
        "maxVisibilitySamples": 4,
        "shadingRayDepth": 2,
        "reflectionRayDepth": 2,
        "refractionRayDepth": 4,
    },
    "high": {
        "edgeAntiAliasing": 3,
        "shadingSamples": 4,
        "maxShadingSamples": 8,
        "visibilitySamples": 4,
        "maxVisibilitySamples": 8,
        "shadingRayDepth": 4,
        "reflectionRayDepth": 4,
        "refractionRayDepth": 6,
    },
}


def set_render_quality(preset: str = "medium") -> dict:
    """Apply a render quality preset to the Maya Software render globals.

    Presets control anti-aliasing, shading samples and ray depth on the
    ``defaultRenderQuality`` node.

    Args:
        preset: One of ``"low"``, ``"medium"``, or ``"high"``.
            Default: ``"medium"``.

    Returns:
        ActionResultModel dict with ``context.preset`` and
        ``context.applied`` (dict of attribute names and values set).
    """

    preset_key = preset.lower()
    if preset_key not in _RENDER_QUALITY_PRESETS:
        return maya_error(
            "Invalid preset: {}".format(preset),
            "Supported presets: {}".format(", ".join(sorted(_RENDER_QUALITY_PRESETS))),
        )

    attrs = _RENDER_QUALITY_PRESETS[preset_key]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        node = "defaultRenderQuality"
        applied = {}
        for attr_name, value in attrs.items():
            plug = "{}.{}".format(node, attr_name)
            if cmds.objExists(plug):
                cmds.setAttr(plug, value)
                applied[attr_name] = value

        return maya_success(
            "Applied '{}' render quality preset".format(preset_key),
            preset=preset_key,
            applied=applied,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set render quality preset '{}'".format(preset))


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

        return maya_success(
            "Scene render stats: {} @ {}x{}".format(renderer, width, height),
            renderer=renderer,
            width=width,
            height=height,
            start_frame=start_frame,
            end_frame=end_frame,
            output_file_prefix=output_prefix,
            quality=quality,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to query scene render stats")
