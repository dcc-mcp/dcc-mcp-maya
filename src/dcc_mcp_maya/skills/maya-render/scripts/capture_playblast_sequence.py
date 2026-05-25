"""Capture a Maya playblast image sequence to disk."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_MAX_PLAYBLAST_DIM = 8192
_SAFE_PREFIX_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _clamp_playblast_dims(width: int, height: int) -> Tuple[int, int]:
    w = max(1, min(int(width), _MAX_PLAYBLAST_DIM))
    h = max(1, min(int(height), _MAX_PLAYBLAST_DIM))
    return w, h


def _safe_prefix(prefix: str) -> str:
    value = _SAFE_PREFIX_RE.sub("_", str(prefix or "mcp_playblast")).strip("._")
    return value or "mcp_playblast"


def _frame_range(cmds: Any, start_frame: Optional[float], end_frame: Optional[float]) -> Tuple[int, int]:
    if start_frame is None:
        try:
            start_frame = cmds.playbackOptions(query=True, minTime=True)
        except Exception:  # noqa: BLE001
            start_frame = cmds.currentTime(query=True)
    if end_frame is None:
        try:
            end_frame = cmds.playbackOptions(query=True, maxTime=True)
        except Exception:  # noqa: BLE001
            end_frame = start_frame
    f0 = int(round(float(start_frame)))
    f1 = int(round(float(end_frame)))
    if f1 < f0:
        f0, f1 = f1, f0
    return f0, f1


def _no_visible_panel(cmds: Any) -> bool:
    try:
        panels = cmds.getPanel(type="modelPanel") or []
        visible = cmds.getPanel(visiblePanels=True) or []
        return not any(panel in visible for panel in panels)
    except Exception:  # noqa: BLE001
        return False


def _active_model_panel(cmds: Any) -> Optional[str]:
    try:
        focused = cmds.getPanel(withFocus=True)
        if focused and cmds.getPanel(typeOf=focused) == "modelPanel":
            return str(focused)
    except Exception:  # noqa: BLE001
        pass
    try:
        panels = cmds.getPanel(type="modelPanel") or []
        visible = set(cmds.getPanel(visiblePanels=True) or [])
    except Exception:  # noqa: BLE001
        return None
    for panel in panels:
        if panel in visible:
            return str(panel)
    return str(panels[0]) if panels else None


def _camera_from_panel(cmds: Any, panel: Optional[str]) -> Optional[str]:
    if not panel:
        return None
    try:
        return str(cmds.modelPanel(panel, query=True, camera=True))
    except Exception:  # noqa: BLE001
        return None


def _look_through_camera(cmds: Any, panel: Optional[str], camera: Optional[str]) -> Optional[str]:
    if not panel or not camera:
        return None
    previous = _camera_from_panel(cmds, panel)
    try:
        cmds.lookThru(panel, camera)
    except Exception:  # noqa: BLE001
        return None
    return previous


def _restore_camera(cmds: Any, panel: Optional[str], previous_camera: Optional[str]) -> None:
    if not panel or not previous_camera:
        return
    try:
        cmds.lookThru(panel, previous_camera)
    except Exception:  # noqa: BLE001
        pass


def _apply_view_fit(cmds: Any, panel: Optional[str]) -> bool:
    try:
        if panel:
            cmds.viewFit(panel, allObjects=True, animate=False)
        else:
            cmds.viewFit(allObjects=True, animate=False)
        return True
    except Exception:  # noqa: BLE001
        return False


def _matching_sequence_files(
    output_dir: Path, prefix: str, compression: str, start_frame: int, end_frame: int
) -> List[str]:
    suffix = "." + compression.lower().lstrip(".")
    names = []
    for frame in range(start_frame, end_frame + 1):
        names.extend(
            [
                "{}.{:04d}{}".format(prefix, frame, suffix),
                "{}.{}{}".format(prefix, frame, suffix),
            ]
        )
    direct = output_dir / "{}{}".format(prefix, suffix)
    candidates = [output_dir / name for name in names]
    if start_frame == end_frame:
        candidates.append(direct)
    existing = [str(path) for path in candidates if path.exists()]
    if existing:
        return existing
    return [
        str(output_dir / name)
        for name in sorted(os.listdir(str(output_dir)))
        if name.startswith(prefix + ".") and name.lower().endswith(suffix)
    ]


def _nonempty_or_error(paths: List[str]) -> Optional[dict]:
    empty = [path for path in paths if os.path.exists(path) and os.path.getsize(path) == 0]
    if not empty:
        return None
    return skill_error(
        "Playblast sequence produced empty image file(s)",
        "Maya playblast wrote one or more 0-byte image files.",
        error_code="EMPTY_PLAYBLAST_SEQUENCE",
        empty_files=empty,
    )


def _safe_get_attr(cmds: Any, plug: str) -> Any:
    try:
        exists = getattr(cmds, "objExists", None)
        if callable(exists) and not exists(plug):
            return None
    except Exception:  # noqa: BLE001
        pass
    try:
        value = cmds.getAttr(plug)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], tuple):
        return list(value[0])
    return value


def _camera_shape(cmds: Any, camera: Optional[str]) -> Optional[str]:
    if not camera:
        return None
    try:
        if cmds.nodeType(camera) == "camera":
            return str(camera)
    except Exception:  # noqa: BLE001
        pass
    try:
        shapes = cmds.listRelatives(camera, shapes=True, fullPath=False) or []
    except Exception:  # noqa: BLE001
        shapes = []
    for shape in shapes:
        try:
            if cmds.nodeType(shape) == "camera":
                return str(shape)
        except Exception:  # noqa: BLE001
            continue
    return None


def _camera_metadata(cmds: Any, camera: Optional[str]) -> Dict[str, Any]:
    shape = _camera_shape(cmds, camera)
    return {
        "camera": camera,
        "camera_shape": shape,
        "translate": _safe_get_attr(cmds, "{}.translate".format(camera)) if camera else None,
        "rotate": _safe_get_attr(cmds, "{}.rotate".format(camera)) if camera else None,
        "focal_length": _safe_get_attr(cmds, "{}.focalLength".format(shape)) if shape else None,
        "horizontal_film_aperture": _safe_get_attr(cmds, "{}.horizontalFilmAperture".format(shape)) if shape else None,
        "vertical_film_aperture": _safe_get_attr(cmds, "{}.verticalFilmAperture".format(shape)) if shape else None,
        "near_clip_plane": _safe_get_attr(cmds, "{}.nearClipPlane".format(shape)) if shape else None,
        "far_clip_plane": _safe_get_attr(cmds, "{}.farClipPlane".format(shape)) if shape else None,
    }


def capture_playblast_sequence(
    output_dir: Optional[str] = None,
    prefix: str = "mcp_playblast",
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    width: int = 1920,
    height: int = 1080,
    percent: int = 100,
    compression: str = "png",
    off_screen: Optional[bool] = None,
    show_ornaments: bool = False,
    view_fit: bool = False,
    camera: Optional[str] = None,
    include_camera_metadata: bool = True,
) -> dict:
    """Write a playblast image sequence and return the generated file list."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        created_temp_dir = False
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="dcc_mcp_maya_playblast_")
            created_temp_dir = True
        out_dir = Path(os.path.expandvars(os.path.expanduser(str(output_dir))))
        out_dir.mkdir(parents=True, exist_ok=True)

        safe_prefix = _safe_prefix(prefix)
        width, height = _clamp_playblast_dims(width, height)
        percent = max(1, min(int(percent), 100))
        compression = str(compression or "png").lower().lstrip(".")
        if compression not in {"png", "jpg", "jpeg"}:
            return skill_error(
                "Unsupported playblast image format",
                "compression must be one of: png, jpg, jpeg",
                compression=compression,
            )

        f0, f1 = _frame_range(cmds, start_frame, end_frame)
        panel = _active_model_panel(cmds)
        previous_camera = _look_through_camera(cmds, panel, camera)
        active_camera = camera or _camera_from_panel(cmds, panel)
        view_fit_applied = False
        if view_fit:
            view_fit_applied = _apply_view_fit(cmds, panel)
        if off_screen is None:
            off_screen = bool(cmds.about(batch=True)) or _no_visible_panel(cmds)
        if view_fit and not view_fit_applied:
            off_screen = True

        prefix_path = str(out_dir / safe_prefix)
        try:
            cmds.playblast(
                startTime=f0,
                endTime=f1,
                format="image",
                compression=compression,
                filename=prefix_path,
                width=width,
                height=height,
                percent=percent,
                viewer=False,
                showOrnaments=bool(show_ornaments),
                offScreen=bool(off_screen),
                forceOverwrite=True,
            )
        finally:
            _restore_camera(cmds, panel, previous_camera)

        files = _matching_sequence_files(out_dir, safe_prefix, compression, f0, f1)
        if not files:
            return skill_error(
                "Playblast sequence files not found",
                "Could not locate image sequence output from Maya playblast.",
                output_dir=str(out_dir),
                prefix=safe_prefix,
                start_frame=f0,
                end_frame=f1,
            )
        empty_error = _nonempty_or_error(files)
        if empty_error:
            return empty_error

        return skill_success(
            "Captured {} playblast frame(s)".format(len(files)),
            files=files,
            output_dir=str(out_dir),
            prefix=safe_prefix,
            start_frame=f0,
            end_frame=f1,
            frame_count=len(files),
            width=width,
            height=height,
            percent=percent,
            compression=compression,
            camera=active_camera,
            camera_metadata=_camera_metadata(cmds, active_camera) if include_camera_metadata else None,
            panel=panel,
            off_screen=bool(off_screen),
            show_ornaments=bool(show_ornaments),
            view_fit=bool(view_fit),
            view_fit_applied=bool(view_fit_applied),
            created_temp_dir=created_temp_dir,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to capture playblast sequence")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`capture_playblast_sequence`."""
    return capture_playblast_sequence(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
