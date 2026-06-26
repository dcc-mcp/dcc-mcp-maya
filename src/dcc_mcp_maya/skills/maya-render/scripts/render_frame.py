"""Render a single Maya frame to disk without using the viewport."""

from __future__ import annotations

import base64
import glob
import os
import re
import tempfile
import time
from typing import Iterable, List, Optional, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_PNG_FORMAT_CODE = 32


def _clamp_dimension(value: Optional[int], fallback: int) -> int:
    try:
        size = int(value if value is not None else fallback)
    except (TypeError, ValueError):
        size = fallback
    return max(1, min(size, 8192))


def _safe_output_name(value: Optional[str]) -> str:
    name = _SAFE_NAME_RE.sub("_", str(value or "mcp_render")).strip("._")
    return name or "mcp_render"


def _escape_mel_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _first_scalar(value):
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _resolve_camera(cmds, camera: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return ``(camera_transform, camera_shape, source)``."""

    if camera:
        if not cmds.objExists(camera):
            return None, None, "missing"
        node_type = cmds.nodeType(camera)
        if node_type == "camera":
            parents = cmds.listRelatives(camera, parent=True, fullPath=False) or []
            return (_first_scalar(parents) or camera), camera, "explicit_shape"
        shapes = cmds.listRelatives(camera, shapes=True, type="camera", fullPath=False) or []
        return camera, _first_scalar(shapes), "explicit_transform"

    renderable_shapes = cmds.ls(type="camera") or []
    for shape in renderable_shapes:
        try:
            if cmds.getAttr("{}.renderable".format(shape)):
                parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
                parent = _first_scalar(parents)
                if parent:
                    return parent, shape, "renderable_camera"
        except Exception:
            continue

    if cmds.objExists("persp"):
        shapes = cmds.listRelatives("persp", shapes=True, type="camera", fullPath=False) or []
        return "persp", _first_scalar(shapes), "fallback_persp"
    return None, None, "none"


def _workspace_render_dir(cmds) -> str:
    try:
        root = cmds.workspace(q=True, rootDirectory=True)
        images_rule = cmds.workspace(q=True, fileRuleEntry="images") or "images"
        if os.path.isabs(images_rule):
            return images_rule
        return os.path.join(root, images_rule)
    except Exception:
        return tempfile.mkdtemp(prefix="dcc_mcp_maya_render_")


def _paths_from_render_result(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        paths = []
        for item in value:
            paths.extend(_paths_from_render_result(item))
        return paths
    text = str(value)
    if text:
        return [text]
    return []


def _candidate_paths(prefix: str, output_dir: str, render_result) -> List[str]:
    candidates = []
    candidates.extend(_paths_from_render_result(render_result))
    candidates.extend(glob.glob(prefix + "*"))
    candidates.extend(glob.glob(os.path.join(output_dir, "*")))

    seen = set()
    ordered = []
    for path in candidates:
        if not path:
            continue
        norm = os.path.abspath(path)
        if norm not in seen and os.path.isfile(norm):
            seen.add(norm)
            ordered.append(norm)
    ordered.sort(key=lambda item: os.path.getmtime(item), reverse=True)
    return ordered


def _pick_nonempty_output(paths: Iterable[str], started_at: float) -> Tuple[Optional[str], List[str]]:
    empty_paths = []
    for path in paths:
        try:
            if os.path.getmtime(path) + 1.0 < started_at:
                continue
            size = os.path.getsize(path)
        except OSError:
            continue
        if size > 0:
            return path, empty_paths
        empty_paths.append(path)
    return None, empty_paths


def _read_optional_base64(path: str, return_base64: bool) -> Optional[str]:
    if not return_base64:
        return None
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def _get_attr_or_none(cmds, attr: str):
    try:
        return cmds.getAttr(attr)
    except Exception:
        return None


def _set_string_attr(cmds, attr: str, value: str) -> None:
    cmds.setAttr(attr, value, type="string")


def render_frame(
    camera: Optional[str] = None,
    frame: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    output_dir: Optional[str] = None,
    output_name: Optional[str] = None,
    return_base64: bool = True,
) -> dict:
    """Render one frame to disk using the active renderer.

    This is intentionally independent of model panels and playblast, so it can
    still produce imagery when Maya is minimized or the viewport is unavailable.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer") or "mayaSoftware"
        previous_frame = cmds.currentTime(q=True)
        target_frame = float(frame if frame is not None else previous_frame)
        previous_width = _get_attr_or_none(cmds, "defaultResolution.width")
        previous_height = _get_attr_or_none(cmds, "defaultResolution.height")
        previous_format = _get_attr_or_none(cmds, "defaultRenderGlobals.imageFormat")
        previous_prefix = _get_attr_or_none(cmds, "defaultRenderGlobals.imageFilePrefix")

        target_width = _clamp_dimension(width, int(previous_width or 1920))
        target_height = _clamp_dimension(height, int(previous_height or 1080))
        camera_name, camera_shape, camera_source = _resolve_camera(cmds, camera)
        if not camera_name:
            return skill_error(
                "No renderable camera found",
                "Specify a valid camera transform or create a renderable camera before calling render_frame.",
                possible_solutions=[
                    "Pass camera='persp' for a default perspective render.",
                    "Create a camera with maya_scene__create_camera and render that camera.",
                ],
                camera=camera,
                camera_source=camera_source,
            )

        target_dir = output_dir or _workspace_render_dir(cmds)
        os.makedirs(target_dir, exist_ok=True)
        prefix = os.path.join(target_dir, _safe_output_name(output_name))
        started_at = time.time()
        render_result = None

        try:
            cmds.currentTime(target_frame)
            cmds.setAttr("defaultResolution.width", target_width)
            cmds.setAttr("defaultResolution.height", target_height)
            cmds.setAttr("defaultRenderGlobals.imageFormat", _PNG_FORMAT_CODE)
            _set_string_attr(cmds, "defaultRenderGlobals.imageFilePrefix", prefix)

            if renderer == "arnold":
                try:
                    mtoa_loaded = bool(cmds.pluginInfo("mtoa", q=True, loaded=True))
                except Exception:
                    mtoa_loaded = False
                if not mtoa_loaded:
                    return skill_error(
                        "Arnold renderer is selected but MtoA is not loaded",
                        "Load the mtoa plugin or switch defaultRenderGlobals.currentRenderer to mayaSoftware.",
                        possible_solutions=[
                            "Call cmds.loadPlugin('mtoa') before rendering with Arnold.",
                            "Use maya_render__set_render_settings(renderer='mayaSoftware') for a software fallback.",
                        ],
                        renderer=renderer,
                        camera=camera_name,
                    )
                import maya.mel as mel  # noqa: PLC0415

                command = 'arnoldRender -camera "{}" -frame {}'.format(
                    _escape_mel_string(camera_name),
                    target_frame,
                )
                render_result = mel.eval(command)
            else:
                render_result = cmds.render(camera_name, x=target_width, y=target_height)
        finally:
            try:
                if previous_width is not None:
                    cmds.setAttr("defaultResolution.width", previous_width)
                if previous_height is not None:
                    cmds.setAttr("defaultResolution.height", previous_height)
                if previous_format is not None:
                    cmds.setAttr("defaultRenderGlobals.imageFormat", previous_format)
                if previous_prefix is not None:
                    _set_string_attr(cmds, "defaultRenderGlobals.imageFilePrefix", previous_prefix or "")
                cmds.currentTime(previous_frame)
            except Exception:
                pass

        candidates = _candidate_paths(prefix, target_dir, render_result)
        output_path, empty_paths = _pick_nonempty_output(candidates, started_at)
        if not output_path:
            return skill_error(
                "Render did not produce a non-empty image",
                "No rendered file was found, or Maya wrote a 0-byte image.",
                possible_solutions=[
                    "Verify the selected renderer can render in this Maya session.",
                    "Try renderer='mayaSoftware' via set_render_settings if Arnold is unavailable.",
                    "Check that the camera sees scene geometry and the output directory is writable.",
                ],
                error_code="EMPTY_RENDER",
                renderer=renderer,
                camera=camera_name,
                output_dir=target_dir,
                output_prefix=prefix,
                empty_paths=empty_paths,
                render_result=render_result,
            )

        image_base64 = _read_optional_base64(output_path, return_base64)
        context = {
            "renderer": renderer,
            "camera": camera_name,
            "camera_shape": camera_shape,
            "camera_source": camera_source,
            "frame": target_frame,
            "width": target_width,
            "height": target_height,
            "output_path": output_path,
            "output_size": os.path.getsize(output_path),
            "output_prefix": prefix,
            "image_base64": image_base64,
        }
        if render_result is not None:
            context["render_result"] = render_result
        return skill_success(
            "Rendered frame {} to {}".format(target_frame, output_path),
            prompt="Use output_path for downstream publishing, or image_base64 for quick visual inspection.",
            **context,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to render frame")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`render_frame`."""
    return render_frame(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
