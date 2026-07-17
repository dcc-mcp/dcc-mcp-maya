"""Deterministic house designs authored as evaluated Bifrost mesh graphs."""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dcc_mcp_maya.bifrost import (
    add_node,
    connect_ports,
    create_graph,
    create_port,
    set_port_default,
)

HOUSE_STYLES: Tuple[str, ...] = ("cabin", "cottage", "modern", "townhouse")
MAX_HOUSE_SEED = 2_147_483_647


class HouseContractError(ValueError):
    """Raised when a procedural-house request violates the public contract."""


@dataclass(frozen=True)
class HousePart:
    """One primitive in a house design.

    ``anchor`` is the cube centre for ``cube`` parts and the bottom-centre for
    ``gable`` parts. Dimensions always use width (X), height (Y), depth (Z).
    """

    name: str
    kind: str
    dimensions: Tuple[float, float, float]
    anchor: Tuple[float, float, float]


@dataclass(frozen=True)
class HouseSpec:
    """A deterministic, host-independent house design."""

    style: str
    seed: int
    origin: Tuple[float, float, float]
    parts: Tuple[HousePart, ...]


def _rounded(value: float) -> float:
    return round(float(value), 3)


def _uniform(rng: random.Random, minimum: float, maximum: float) -> float:
    return _rounded(rng.uniform(minimum, maximum))


def _part(
    name: str,
    kind: str,
    dimensions: Sequence[float],
    anchor: Sequence[float],
) -> HousePart:
    return HousePart(
        name=name,
        kind=kind,
        dimensions=tuple(_rounded(value) for value in dimensions),  # type: ignore[arg-type]
        anchor=tuple(_rounded(value) for value in anchor),  # type: ignore[arg-type]
    )


def _cottage(rng: random.Random) -> List[HousePart]:
    width = _uniform(rng, 5.8, 7.4)
    depth = _uniform(rng, 4.8, 6.2)
    wall_height = _uniform(rng, 3.2, 4.0)
    roof_height = _uniform(rng, 2.0, 2.8)
    return [
        _part("walls", "cube", (width, wall_height, depth), (0, wall_height / 2, 0)),
        _part("gable_roof", "gable", (width + 0.8, roof_height, depth + 0.8), (0, wall_height, 0)),
        _part("front_step", "cube", (width * 0.42, 0.35, 1.2), (0, 0.175, depth / 2 + 0.5)),
        _part("porch_canopy", "cube", (width * 0.46, 0.28, 1.35), (0, wall_height * 0.72, depth / 2 + 0.52)),
        _part("chimney", "cube", (0.65, 2.0, 0.65), (width * 0.24, wall_height + roof_height * 0.55, -depth * 0.15)),
    ]


def _cabin(rng: random.Random) -> List[HousePart]:
    width = _uniform(rng, 7.5, 9.4)
    depth = _uniform(rng, 5.5, 7.0)
    wall_height = _uniform(rng, 2.8, 3.5)
    roof_height = _uniform(rng, 2.5, 3.4)
    porch_depth = _uniform(rng, 1.4, 2.0)
    return [
        _part("log_walls", "cube", (width, wall_height, depth), (0, wall_height / 2, 0)),
        _part("steep_roof", "gable", (width + 1.1, roof_height, depth + 1.0), (0, wall_height, 0)),
        _part("porch_deck", "cube", (width * 0.78, 0.32, porch_depth), (0, 0.16, depth / 2 + porch_depth / 2)),
        _part(
            "porch_roof",
            "cube",
            (width * 0.72, 0.3, porch_depth + 0.25),
            (0, wall_height * 0.76, depth / 2 + porch_depth / 2),
        ),
        _part(
            "porch_post_left",
            "cube",
            (0.24, wall_height * 0.72, 0.24),
            (-width * 0.3, wall_height * 0.36, depth / 2 + porch_depth * 0.72),
        ),
        _part(
            "porch_post_right",
            "cube",
            (0.24, wall_height * 0.72, 0.24),
            (width * 0.3, wall_height * 0.36, depth / 2 + porch_depth * 0.72),
        ),
        _part(
            "stone_chimney", "cube", (0.8, 2.3, 0.8), (-width * 0.27, wall_height + roof_height * 0.58, -depth * 0.12)
        ),
    ]


def _modern(rng: random.Random) -> List[HousePart]:
    width = _uniform(rng, 6.5, 8.2)
    depth = _uniform(rng, 5.2, 6.8)
    ground_height = _uniform(rng, 3.0, 3.8)
    upper_height = _uniform(rng, 2.5, 3.2)
    return [
        _part("ground_volume", "cube", (width * 0.78, ground_height, depth), (-width * 0.11, ground_height / 2, 0)),
        _part(
            "side_volume",
            "cube",
            (width * 0.34, ground_height * 0.72, depth * 0.72),
            (width * 0.43, ground_height * 0.36, depth * 0.08),
        ),
        _part(
            "upper_volume",
            "cube",
            (width * 0.7, upper_height, depth * 0.76),
            (width * 0.12, ground_height + upper_height / 2, -depth * 0.08),
        ),
        _part("ground_roof", "cube", (width * 0.84, 0.24, depth + 0.35), (-width * 0.11, ground_height + 0.12, 0)),
        _part(
            "upper_roof",
            "cube",
            (width * 0.76, 0.24, depth * 0.82),
            (width * 0.12, ground_height + upper_height + 0.12, -depth * 0.08),
        ),
        _part(
            "entry_canopy", "cube", (width * 0.34, 0.22, 1.45), (-width * 0.2, ground_height * 0.68, depth / 2 + 0.55)
        ),
    ]


def _townhouse(rng: random.Random) -> List[HousePart]:
    width = _uniform(rng, 3.8, 5.0)
    depth = _uniform(rng, 5.4, 6.8)
    floor_height = _uniform(rng, 2.7, 3.1)
    floors = rng.choice((2, 3))
    height = _rounded(floor_height * floors)
    parapet_height = 0.55
    return [
        _part("tower", "cube", (width, height, depth), (0, height / 2, 0)),
        _part("roof_slab", "cube", (width + 0.3, 0.25, depth + 0.3), (0, height + 0.125, 0)),
        _part(
            "parapet_front",
            "cube",
            (width + 0.3, parapet_height, 0.22),
            (0, height + parapet_height / 2, depth / 2 + 0.04),
        ),
        _part(
            "parapet_back",
            "cube",
            (width + 0.3, parapet_height, 0.22),
            (0, height + parapet_height / 2, -depth / 2 - 0.04),
        ),
        _part(
            "parapet_left", "cube", (0.22, parapet_height, depth), (-width / 2 - 0.04, height + parapet_height / 2, 0)
        ),
        _part(
            "parapet_right", "cube", (0.22, parapet_height, depth), (width / 2 + 0.04, height + parapet_height / 2, 0)
        ),
        _part(
            "front_bay", "cube", (width * 0.56, floor_height * 0.78, 0.65), (0, floor_height * 1.28, depth / 2 + 0.3)
        ),
        _part("door_canopy", "cube", (width * 0.45, 0.22, 1.0), (0, floor_height * 0.78, depth / 2 + 0.42)),
    ]


_STYLE_BUILDERS = {
    "cabin": _cabin,
    "cottage": _cottage,
    "modern": _modern,
    "townhouse": _townhouse,
}


def resolve_house_seed(seed: Optional[int]) -> int:
    """Return a valid seed, generating one when the caller omits it."""
    if seed is None:
        return random.SystemRandom().randint(0, MAX_HOUSE_SEED)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise HouseContractError("seed must be an integer")
    if seed < 0 or seed > MAX_HOUSE_SEED:
        raise HouseContractError("seed must be between 0 and {}".format(MAX_HOUSE_SEED))
    return seed


def normalize_house_name(name: Optional[str]) -> str:
    """Return a Maya-safe base name for the generated transform."""
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(name or "ProceduralHouse").strip()).strip("_")
    if not value:
        value = "ProceduralHouse"
    if value[0].isdigit():
        value = "House_" + value
    return value


def design_house(
    seed: Optional[int] = None,
    style: str = "random",
    position: Optional[Sequence[float]] = None,
) -> HouseSpec:
    """Create a deterministic house specification without importing Maya."""
    resolved_seed = resolve_house_seed(seed)
    requested_style = str(style or "random").strip().lower()
    if requested_style not in HOUSE_STYLES + ("random",):
        raise HouseContractError("style must be one of: random, {}".format(", ".join(HOUSE_STYLES)))
    origin_values = tuple(position or (0.0, 0.0, 0.0))
    if len(origin_values) != 3:
        raise HouseContractError("position must contain exactly three numbers")
    try:
        origin = tuple(_rounded(value) for value in origin_values)
    except (TypeError, ValueError):
        raise HouseContractError("position must contain exactly three numbers")

    rng = random.Random(resolved_seed)
    resolved_style = rng.choice(HOUSE_STYLES) if requested_style == "random" else requested_style
    local_parts = _STYLE_BUILDERS[resolved_style](rng)
    ox, oy, oz = origin
    parts = tuple(
        HousePart(
            name=part.name,
            kind=part.kind,
            dimensions=part.dimensions,
            anchor=(
                _rounded(part.anchor[0] + ox),
                _rounded(part.anchor[1] + oy),
                _rounded(part.anchor[2] + oz),
            ),
        )
        for part in local_parts
    )
    return HouseSpec(style=resolved_style, seed=resolved_seed, origin=origin, parts=parts)


def house_spec_to_dict(spec: HouseSpec) -> Dict[str, Any]:
    """Serialize a house specification into a stable JSON-compatible shape."""
    return {
        "style": spec.style,
        "seed": spec.seed,
        "origin": list(spec.origin),
        "parts": [
            {
                "name": part.name,
                "kind": part.kind,
                "dimensions": list(part.dimensions),
                "anchor": list(part.anchor),
            }
            for part in spec.parts
        ],
    }


def _build_cube(cmds: Any, graph: str, part: HousePart) -> str:
    node = add_node(cmds, graph, "Modeling::Primitive::create_mesh_cube", name=part.name)
    width, height, depth = part.dimensions
    for port, value in (
        ("length", depth),
        ("width", width),
        ("height", height),
        ("position", part.anchor),
    ):
        set_port_default(cmds, graph, node, port, value)
    return ".{}.cube_mesh".format(node)


def _build_gable(cmds: Any, graph: str, part: HousePart) -> str:
    primitive = add_node(cmds, graph, "Modeling::Primitive::create_mesh_cylinder", name=part.name)
    width, height, depth = part.dimensions
    for port, value in (
        ("radius", 1.0),
        ("height", depth),
        ("axis_segments", 3),
        ("height_segments", 1),
        ("position", (0.0, 0.0, 0.0)),
        ("up_axis", (0.0, 0.0, 1.0)),
    ):
        set_port_default(cmds, graph, primitive, port, value)

    orient = add_node(
        cmds,
        graph,
        "Modeling::Points::transform_points",
        name="{}_orient".format(part.name),
    )
    x, base_y, z = part.anchor
    matrix = (
        width / math.sqrt(3.0),
        0.0,
        0.0,
        0.0,
        0.0,
        -(height / 1.5),
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        x,
        base_y + height / 3.0,
        z,
        1.0,
    )
    set_port_default(cmds, graph, orient, "transform", tuple(_rounded(value) for value in matrix))
    connect_ports(cmds, graph, ".{}.out_mesh".format(primitive), ".{}.points".format(orient))
    return ".{}.out_points".format(orient)


def build_house_graph(cmds: Any, spec: HouseSpec, name: Optional[str] = None) -> Dict[str, Any]:
    """Build and evaluate one house specification as a Bifrost graph shape."""
    house_name = normalize_house_name(name)
    graph_record = create_graph(cmds, name=house_name + "Shape", kind="graph_shape")
    graph = graph_record["graph"]
    outputs: List[str] = []
    for part in spec.parts:
        if part.kind == "cube":
            outputs.append(_build_cube(cmds, graph, part))
        elif part.kind == "gable":
            outputs.append(_build_gable(cmds, graph, part))
        else:
            raise HouseContractError("unsupported house part kind: {}".format(part.kind))

    array_node = add_node(cmds, graph, "Core::Array::build_array", name="house_parts")
    for index, source in enumerate(outputs):
        port = "part_{:02d}".format(index)
        create_port(cmds, graph, array_node, port, "Object")
        connect_ports(cmds, graph, source, ".{}.{}".format(array_node, port))
    merge_node = add_node(cmds, graph, "Modeling::Common::merge_geometry", name="merge_house")
    connect_ports(cmds, graph, ".{}.array".format(array_node), ".{}.geometry".format(merge_node))
    create_port(cmds, graph, "output", "house", "Object")
    connect_ports(cmds, graph, ".{}.merged".format(merge_node), ".output.house")
    cmds.dgdirty(graph)

    transform = graph_record.get("transform")
    bounds = [float(value) for value in (cmds.exactWorldBoundingBox(transform) if transform else [])]
    nodes = [str(value) for value in (cmds.vnnCompound(graph, ".", listNodes=True) or [])]
    result = dict(graph_record)
    result.update(
        {
            "name": house_name,
            "style": spec.style,
            "seed": spec.seed,
            "part_count": len(spec.parts),
            "node_count": len(nodes),
            "nodes": nodes,
            "bounds": bounds,
            "spec": house_spec_to_dict(spec),
        }
    )
    return result
