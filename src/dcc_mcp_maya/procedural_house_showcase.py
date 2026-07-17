"""Deterministic Maya scene staging for procedural-house showcases."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dcc_mcp_maya.procedural_house import (
    HOUSE_STYLES,
    MAX_HOUSE_SEED,
    HouseContractError,
    build_house_graph,
    design_house,
    normalize_house_name,
    resolve_house_seed,
)

SHOWCASE_COLORS: Tuple[Tuple[float, float, float], ...] = (
    (0.36, 0.18, 0.08),
    (0.74, 0.46, 0.24),
    (0.18, 0.46, 0.62),
    (0.56, 0.20, 0.16),
)
MIN_SHOWCASE_FRAMES = 24
MAX_SHOWCASE_FRAMES = 240


class HouseShowcaseContractError(HouseContractError):
    """Raised when a procedural-house showcase request is invalid."""


@dataclass(frozen=True)
class HouseShowcaseEntry:
    """One deterministic house placement in a showcase."""

    style: str
    seed: int
    position: Tuple[float, float, float]
    color: Tuple[float, float, float]
    reveal_frame: int


@dataclass(frozen=True)
class HouseShowcaseSpec:
    """Host-independent staging contract shared by GUI and standalone Maya."""

    name: str
    seed: int
    origin: Tuple[float, float, float]
    spacing: float
    frame_count: int
    entries: Tuple[HouseShowcaseEntry, ...]


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise HouseShowcaseContractError("{} must be a finite number".format(label))
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise HouseShowcaseContractError("{} must be a finite number".format(label))
    if not math.isfinite(number):
        raise HouseShowcaseContractError("{} must be a finite number".format(label))
    return round(number, 3)


def design_house_showcase(
    seed: Optional[int] = None,
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    spacing: float = 9.0,
    frame_count: int = 72,
) -> HouseShowcaseSpec:
    """Create a deterministic four-style showcase without importing Maya."""
    resolved_seed = resolve_house_seed(seed)
    origin_values = tuple(position or (0.0, 0.0, 0.0))
    if len(origin_values) != 3:
        raise HouseShowcaseContractError("position must contain exactly three numbers")
    origin = tuple(_finite_number(value, "position") for value in origin_values)
    resolved_spacing = _finite_number(spacing, "spacing")
    if resolved_spacing < 6.0 or resolved_spacing > 30.0:
        raise HouseShowcaseContractError("spacing must be between 6 and 30")
    if isinstance(frame_count, bool) or not isinstance(frame_count, int):
        raise HouseShowcaseContractError("frame_count must be an integer")
    if frame_count < MIN_SHOWCASE_FRAMES or frame_count > MAX_SHOWCASE_FRAMES:
        raise HouseShowcaseContractError(
            "frame_count must be between {} and {}".format(MIN_SHOWCASE_FRAMES, MAX_SHOWCASE_FRAMES)
        )

    reveal_interval = max(4, frame_count // (len(HOUSE_STYLES) + 2))
    centre_index = (len(HOUSE_STYLES) - 1) / 2.0
    entries = []
    for index, style in enumerate(HOUSE_STYLES):
        house_seed = (resolved_seed + index) % (MAX_HOUSE_SEED + 1)
        entries.append(
            HouseShowcaseEntry(
                style=style,
                seed=house_seed,
                position=(
                    round(origin[0] + (index - centre_index) * resolved_spacing, 3),
                    origin[1],
                    origin[2],
                ),
                color=SHOWCASE_COLORS[index],
                reveal_frame=1 + index * reveal_interval,
            )
        )
    return HouseShowcaseSpec(
        name=normalize_house_name(name or "ProceduralHouseShowcase"),
        seed=resolved_seed,
        origin=origin,  # type: ignore[arg-type]
        spacing=resolved_spacing,
        frame_count=frame_count,
        entries=tuple(entries),
    )


def showcase_spec_to_dict(spec: HouseShowcaseSpec) -> Dict[str, Any]:
    """Serialize a showcase specification into a stable JSON-compatible shape."""
    return {
        "name": spec.name,
        "seed": spec.seed,
        "origin": list(spec.origin),
        "spacing": spec.spacing,
        "frame_count": spec.frame_count,
        "entries": [
            {
                "style": entry.style,
                "seed": entry.seed,
                "position": list(entry.position),
                "color": list(entry.color),
                "reveal_frame": entry.reveal_frame,
            }
            for entry in spec.entries
        ],
    }


def _ensure_lambert(cmds: Any, name: str, color: Sequence[float]) -> Dict[str, str]:
    shader_name = "{}Material".format(name)
    shading_group_name = "{}MaterialSG".format(name)
    shader = shader_name
    if not cmds.objExists(shader_name):
        shader = cmds.shadingNode("lambert", asShader=True, name=shader_name)
    shading_group = shading_group_name
    if not cmds.objExists(shading_group_name):
        shading_group = cmds.sets(
            renderable=True,
            noSurfaceShader=True,
            empty=True,
            name=shading_group_name,
        )
    cmds.setAttr("{}.color".format(shader), *color, type="double3")
    cmds.setAttr("{}.diffuse".format(shader), 0.82)
    if not cmds.isConnected("{}.outColor".format(shader), "{}.surfaceShader".format(shading_group)):
        cmds.connectAttr(
            "{}.outColor".format(shader),
            "{}.surfaceShader".format(shading_group),
            force=True,
        )
    return {"shader": str(shader), "shading_group": str(shading_group)}


def _assign_material(cmds: Any, target: str, material: Dict[str, str]) -> None:
    cmds.sets(target, edit=True, forceElement=material["shading_group"])


def _key_house_reveal(cmds: Any, transform: str, reveal_frame: int) -> None:
    for attribute in ("scaleX", "scaleY", "scaleZ"):
        if reveal_frame > 1:
            # Keep Bifrost shapes visible so Viewport 2.0 retains their final
            # draw items while the timeline advances. A near-zero parent scale
            # provides the same staged reveal without visibility invalidation.
            cmds.setKeyframe(transform, attribute=attribute, time=1, value=0.001)
            cmds.setKeyframe(
                transform,
                attribute=attribute,
                time=reveal_frame - 1,
                value=0.001,
            )
        cmds.setKeyframe(transform, attribute=attribute, time=reveal_frame, value=0.05)
        cmds.setKeyframe(transform, attribute=attribute, time=reveal_frame + 6, value=1.0)
        cmds.keyTangent(
            transform,
            attribute=attribute,
            time=(reveal_frame, reveal_frame + 6),
            inTangentType="spline",
            outTangentType="spline",
        )


def _configure_viewports(cmds: Any, camera: str) -> List[str]:
    try:
        panels = [str(value) for value in (cmds.getPanel(type="modelPanel") or [])]
    except Exception:  # noqa: BLE001
        return []
    configured = []
    for panel in panels:
        try:
            cmds.lookThru(panel, camera)
            cmds.modelEditor(
                panel,
                edit=True,
                displayAppearance="smoothShaded",
                displayTextures=True,
                grid=False,
                wireframeOnShaded=False,
                shadows=True,
            )
            configured.append(panel)
        except Exception:  # noqa: BLE001
            continue
    return configured


def _build_camera(cmds: Any, spec: HouseShowcaseSpec, root: str) -> Dict[str, Any]:
    ox, oy, oz = spec.origin
    camera_rig = cmds.group(empty=True, name="{}CameraRig".format(spec.name), parent=root)
    cmds.xform(camera_rig, worldSpace=True, translation=(ox, oy + 2.8, oz))
    camera, camera_shape = cmds.camera(name="{}Camera".format(spec.name))
    camera_distance = max(36.0, spec.spacing * 6.0)
    cmds.xform(camera, worldSpace=True, translation=(ox, oy + 8.5, oz + camera_distance))
    constraint = cmds.aimConstraint(
        camera_rig,
        camera,
        aimVector=(0.0, 0.0, -1.0),
        upVector=(0.0, 1.0, 0.0),
        worldUpType="scene",
    )
    if constraint:
        cmds.delete(constraint)
    cmds.parent(camera, camera_rig)
    cmds.setAttr("{}.focalLength".format(camera_shape), 48.0)
    cmds.setAttr("{}.nearClipPlane".format(camera_shape), 0.1)
    cmds.setAttr("{}.farClipPlane".format(camera_shape), 10000.0)
    cmds.setKeyframe(camera_rig, attribute="rotateY", time=1, value=-16.0)
    cmds.setKeyframe(camera_rig, attribute="rotateY", time=spec.frame_count, value=16.0)
    cmds.keyTangent(
        camera_rig,
        attribute="rotateY",
        time=(1, spec.frame_count),
        inTangentType="linear",
        outTangentType="linear",
    )
    return {
        "camera": str(camera),
        "camera_shape": str(camera_shape),
        "camera_rig": str(camera_rig),
        "camera_distance": camera_distance,
    }


def build_house_showcase(
    cmds: Any,
    spec: HouseShowcaseSpec,
    replace: bool = True,
) -> Dict[str, Any]:
    """Build one staged showcase in the current Maya scene."""
    if replace and cmds.objExists(spec.name):
        cmds.delete(spec.name)
    root = cmds.group(empty=True, name=spec.name)
    houses_group = cmds.group(empty=True, name="{}Houses".format(spec.name), parent=root)

    houses = []
    materials = []
    for index, entry in enumerate(spec.entries):
        house_spec = design_house(seed=entry.seed, style=entry.style, position=entry.position)
        house = build_house_graph(
            cmds,
            house_spec,
            name="{}_{:02d}_{}".format(spec.name, index + 1, entry.style),
        )
        transform = str(house["transform"])
        parented = cmds.parent(transform, houses_group)
        if parented:
            transform = str(parented[0])
        material = _ensure_lambert(cmds, "{}{}".format(spec.name, entry.style.title()), entry.color)
        _assign_material(cmds, transform, material)
        _key_house_reveal(cmds, transform, entry.reveal_frame)
        materials.append(material)
        houses.append(
            {
                "style": entry.style,
                "seed": entry.seed,
                "position": list(entry.position),
                "color": list(entry.color),
                "reveal_frame": entry.reveal_frame,
                "graph": house["graph"],
                "transform": transform,
                "bounds": house.get("bounds", []),
                "part_count": house.get("part_count", 0),
                "node_count": house.get("node_count", 0),
            }
        )

    ground_width = spec.spacing * (len(spec.entries) + 1.5)
    ground_result = cmds.polyPlane(
        name="{}Ground".format(spec.name),
        width=ground_width,
        height=18.0,
        subdivisionsX=1,
        subdivisionsY=1,
        constructionHistory=False,
    )
    ground = str(ground_result[0])
    ground_shapes = cmds.listRelatives(ground, shapes=True, fullPath=True) or []
    ground_shape = str(ground_shapes[0]) if ground_shapes else None
    cmds.xform(ground, worldSpace=True, translation=(spec.origin[0], spec.origin[1] - 0.02, spec.origin[2]))
    cmds.parent(ground, root)
    ground_material = _ensure_lambert(cmds, "{}Ground".format(spec.name), (0.16, 0.18, 0.20))
    _assign_material(cmds, str(ground), ground_material)

    camera_record = _build_camera(cmds, spec, root)
    panels = _configure_viewports(cmds, camera_record["camera"])
    cmds.currentUnit(time="film")
    cmds.playbackOptions(
        minTime=1,
        maxTime=spec.frame_count,
        animationStartTime=1,
        animationEndTime=spec.frame_count,
    )
    cmds.currentTime(spec.frame_count, edit=True)
    cmds.select(root, replace=True)
    return {
        "root": str(root),
        "houses_group": str(houses_group),
        "ground": str(ground),
        "ground_shape": ground_shape,
        "houses": houses,
        "house_count": len(houses),
        "materials": materials + [ground_material],
        "frame_range": [1, spec.frame_count],
        "fps": 24,
        "panels": panels,
        "spec": showcase_spec_to_dict(spec),
        "capture": {
            "skill": "maya-render",
            "tool": "capture_playblast_sequence",
            "arguments": {
                "start_frame": 1,
                "end_frame": spec.frame_count,
                "width": 960,
                "height": 540,
                "compression": "png",
                "camera": camera_record["camera"],
                "show_ornaments": False,
            },
        },
        **camera_record,
    }
