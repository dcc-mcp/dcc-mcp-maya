"""Small, typed boundary around Maya's node-based compositing primitives.

The functions accept a ``maya.cmds``-compatible object so the contract can be
unit tested without importing Maya.  Skill entry points remain responsible for
lazy host imports and result-envelope handling.

This is **not** a render-layer tool: it builds the shading/utility node network
that combines already-rendered imagery (beauty, AOVs, mattes) inside Maya, so
the result can be reviewed or rendered without leaving the scene. It is the
companion to ``render_setup.plan_comp_outputs``, which decides where those
images land on disk.

Everything here was verified against Maya 2025. Behaviours worth knowing:

* ``layeredTexture.inputs`` is a **sparse-ish array**: ``getAttr(s=True)``
  reports 0 before anything is connected and grows as elements are connected,
  so the next free layer index must come from the connected elements, not from
  the attribute size.
* ``grade`` and ``colorCorrect`` exist as node types but ``createNode`` returns
  an ``unknown`` node in a batch session, so they are deliberately not offered.
* ``file.imageName`` does not exist - only ``fileTextureName`` is settable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

#: Layer stack node.
LAYERED_TEXTURE = "layeredTexture"

#: Two-input mix. ``blender`` drives the mix.
BLEND_NODE = "blendColors"

#: Image reader.
FILE_NODE = "file"

#: Utility nodes offered by ``create_comp_node``.
UTILITY_NODES: Tuple[str, ...] = ("reverse", "multiplyDivide", "plusMinusAverage", "luminance", "clamp", "setRange")

#: ``multiplyDivide.operation`` enum, from ``attributeQuery(listEnum=True)``.
MULTIPLY_DIVIDE_OPS: Dict[str, int] = {"none": 0, "multiply": 1, "divide": 2, "power": 3}

#: ``layeredTexture.inputs[N].blendMode`` enum, from ``attributeQuery``.
BLEND_MODES: Tuple[str, ...] = (
    "None",
    "Over",
    "In",
    "Out",
    "Add",
    "Subtract",
    "Multiply",
    "Difference",
    "Lighten",
    "Darken",
    "Saturate",
    "Desaturate",
    "Illuminate",
    "CPV Modulate",
)

#: Merge operations supported by :func:`merge_layers`.
MERGE_OPS: Tuple[str, ...] = ("blend", "over", "add", "multiply", "subtract", "difference")

#: Map a merge operation onto the ``layeredTexture`` blend mode that implements it.
MERGE_TO_BLEND_MODE: Dict[str, str] = {
    "over": "Over",
    "add": "Add",
    "multiply": "Multiply",
    "subtract": "Subtract",
    "difference": "Difference",
}


class CompositingContractError(ValueError):
    """Raised when a compositing operation is malformed."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require(value: str, what: str) -> str:
    name = str(value or "").strip()
    if not name:
        raise CompositingContractError("{} must be a non-empty name".format(what))
    return name


def _resolve(cmds: Any, node: str, what: str = "node") -> str:
    name = _require(node, what)
    if not cmds.objExists(name):
        raise CompositingContractError("Node does not exist: {}".format(name))
    return name


def _connected_indices(cmds: Any, node: str, attr: str = "inputs") -> List[int]:
    """Element indices of ``node.attr`` that currently hold a connection.

    Two Maya behaviours make the obvious approaches wrong (verified on 2025):

    * ``getAttr(node.inputs, size=True)`` reports 0 before the first connection,
      so the attribute size cannot be used to allocate an index.
    * ``listConnections(..., plugs=True)`` on the array returns the SOURCE
      plugs (``f1.outColor``), not the destination elements, so it reveals no
      index either - parsing it silently yields nothing and every layer would
      land on index 0 and overwrite the previous one.

    Probing each element is the only reliable method, and it also exposes the
    holes that disconnecting an element leaves behind.
    """
    connected = cmds.listConnections("{}.{}".format(node, attr), source=True, destination=False) or []
    if not connected:
        return []
    indices: List[int] = []
    for slot in range(len(connected) + len(indices) + 1):
        plug = "{}.{}[{}].color".format(node, attr, slot)
        try:
            sources = cmds.listConnections(plug, source=True, destination=False) or []
        except Exception:  # noqa: BLE001 - an unset element can fail to query
            sources = []
        if sources:
            indices.append(slot)
    return sorted(set(indices))


def _next_index(cmds: Any, node: str, attr: str = "inputs") -> int:
    """Smallest free element index, reusing holes left by removals."""
    occupied = _connected_indices(cmds, node, attr)
    candidate = 0
    for used in occupied:
        if used == candidate:
            candidate += 1
        elif used > candidate:
            break
    return candidate


# ---------------------------------------------------------------------------
# Reading imagery
# ---------------------------------------------------------------------------


def create_image_reader(
    cmds: Any,
    file_path: str,
    name: Optional[str] = None,
    use_frame_extension: bool = False,
    frame_offset: int = 0,
    color_space: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a ``file`` node pointing at on-disk imagery."""
    path = _require(file_path, "file_path")
    node = cmds.createNode(FILE_NODE, name=name) if name else cmds.createNode(FILE_NODE)
    node = str(node)
    cmds.setAttr("{}.fileTextureName".format(node), path, type="string")

    applied: Dict[str, Any] = {"file_path": path}
    if use_frame_extension:
        cmds.setAttr("{}.useFrameExtension".format(node), True)
        applied["use_frame_extension"] = True
        if frame_offset:
            cmds.setAttr("{}.frameOffset".format(node), int(frame_offset))
            applied["frame_offset"] = int(frame_offset)
    if color_space:
        plug = "{}.colorSpace".format(node)
        if cmds.objExists(plug):
            cmds.setAttr(plug, str(color_space), type="string")
            applied["color_space"] = str(color_space)
        else:
            raise CompositingContractError(
                "This Maya build does not expose {}.colorSpace; color management must be "
                "set through the colour management preferences.".format(FILE_NODE)
            )
    return {"node": node, "node_type": FILE_NODE, **applied}


# ---------------------------------------------------------------------------
# Layer stacks
# ---------------------------------------------------------------------------


def create_layer_stack(cmds: Any, name: Optional[str] = None) -> Dict[str, Any]:
    """Create an empty ``layeredTexture`` to stack layers into."""
    node = cmds.createNode(LAYERED_TEXTURE, name=name) if name else cmds.createNode(LAYERED_TEXTURE)
    node = str(node)
    return {"node": node, "node_type": LAYERED_TEXTURE, "layers": 0}


def add_layer(
    cmds: Any,
    stack: str,
    source: str,
    blend_mode: str = "None",
    opacity: float = 1.0,
    visible: bool = True,
) -> Dict[str, Any]:
    """Connect a source's colour into the next free layer of a stack."""
    target = _resolve(cmds, stack, "stack")
    node_type = str(cmds.nodeType(target))
    if node_type != LAYERED_TEXTURE:
        raise CompositingContractError("{} is a {}, expected a {}".format(target, node_type, LAYERED_TEXTURE))
    src = _resolve(cmds, source, "source")

    index = _next_index(cmds, target)
    cmds.connectAttr("{}.outColor".format(src), "{}.inputs[{}].color".format(target, index))

    applied: Dict[str, Any] = {"index": index, "source": src}
    if blend_mode not in BLEND_MODES:
        raise CompositingContractError(
            "Unknown blend mode {}. Supported: {}".format(blend_mode, ", ".join(BLEND_MODES))
        )
    plug = "{}.inputs[{}].blendMode".format(target, index)
    if cmds.objExists(plug):
        cmds.setAttr(plug, BLEND_MODES.index(blend_mode))
        applied["blend_mode"] = blend_mode
    alpha_plug = "{}.inputs[{}].alpha".format(target, index)
    if cmds.objExists(alpha_plug):
        cmds.setAttr(alpha_plug, float(opacity))
        applied["opacity"] = float(opacity)
    visible_plug = "{}.inputs[{}].isVisible".format(target, index)
    if cmds.objExists(visible_plug):
        cmds.setAttr(visible_plug, bool(visible))
        applied["visible"] = bool(visible)
    return {"stack": target, **applied}


def list_layers(cmds: Any, stack: str) -> Dict[str, Any]:
    """Describe the layers currently connected into a stack."""
    target = _resolve(cmds, stack, "stack")
    layers: List[Dict[str, Any]] = []
    for index in _connected_indices(cmds, target):
        sources = (
            cmds.listConnections("{}.inputs[{}].color".format(target, index), source=True, destination=False) or []
        )
        record: Dict[str, Any] = {
            "index": index,
            "source": str(sources[0]) if sources else None,
        }
        mode_plug = "{}.inputs[{}].blendMode".format(target, index)
        if cmds.objExists(mode_plug):
            try:
                record["blend_mode"] = BLEND_MODES[int(cmds.getAttr(mode_plug))]
            except (IndexError, TypeError, ValueError):
                record["blend_mode"] = None
        alpha_plug = "{}.inputs[{}].alpha".format(target, index)
        if cmds.objExists(alpha_plug):
            record["opacity"] = cmds.getAttr(alpha_plug)
        layers.append(record)
    return {"stack": target, "layers": layers, "count": len(layers)}


def remove_layer(cmds: Any, stack: str, index: int) -> Dict[str, Any]:
    """Disconnect one layer from a stack without deleting its source node."""
    target = _resolve(cmds, stack, "stack")
    try:
        slot = int(index)
    except (TypeError, ValueError) as exc:
        raise CompositingContractError("index must be an integer, got {!r}".format(index)) from exc
    if slot < 0:
        raise CompositingContractError("index must be >= 0, got {}".format(slot))

    plug = "{}.inputs[{}].color".format(target, slot)
    sources = cmds.listConnections(plug, source=True, destination=False) or []
    if not sources:
        raise CompositingContractError(
            "Layer {} of {} is empty. Occupied layers: {}".format(
                slot, target, _connected_indices(cmds, target) or "(none)"
            )
        )
    cmds.disconnectAttr("{}.outColor".format(sources[0]), plug)
    return {"stack": target, "removed_index": slot, "source": str(sources[0])}


# ---------------------------------------------------------------------------
# Merging and utilities
# ---------------------------------------------------------------------------


def merge_layers(
    cmds: Any,
    sources: Sequence[str],
    operation: str = "blend",
    name: Optional[str] = None,
    blend_amount: float = 0.5,
) -> Dict[str, Any]:
    """Combine two or more sources into one output.

    ``blend`` uses ``blendColors`` (uniform mix via ``blender``); every other
    operation uses a ``layeredTexture`` stack, whose per-layer blend mode
    implements the operation.
    """
    op = str(operation or "blend").strip().lower()
    if op not in MERGE_OPS:
        raise CompositingContractError("Unknown merge operation {}. Supported: {}".format(op, ", ".join(MERGE_OPS)))
    nodes = [_resolve(cmds, item, "source") for item in (sources or [])]
    if len(nodes) < 2:
        raise CompositingContractError("merge_layers needs at least two sources, got {}".format(len(nodes)))

    if op == "blend":
        if len(nodes) > 2:
            raise CompositingContractError(
                "blend mixes exactly two sources; pass two, or use a layered operation "
                "(over/add/multiply/subtract/difference) for more."
            )
        node = cmds.createNode(BLEND_NODE, name=name) if name else cmds.createNode(BLEND_NODE)
        node = str(node)
        cmds.connectAttr("{}.outColor".format(nodes[0]), "{}.color1".format(node))
        cmds.connectAttr("{}.outColor".format(nodes[1]), "{}.color2".format(node))
        cmds.setAttr("{}.blender".format(node), float(blend_amount))
        return {
            "node": node,
            "node_type": BLEND_NODE,
            "operation": op,
            "sources": nodes,
            "blend_amount": float(blend_amount),
        }

    stack = cmds.createNode(LAYERED_TEXTURE, name=name) if name else cmds.createNode(LAYERED_TEXTURE)
    stack = str(stack)
    for source in nodes:
        add_layer(cmds, stack, source, blend_mode=MERGE_TO_BLEND_MODE[op])
    return {
        "node": stack,
        "node_type": LAYERED_TEXTURE,
        "operation": op,
        "sources": nodes,
        "blend_mode": MERGE_TO_BLEND_MODE[op],
    }


def create_comp_node(
    cmds: Any,
    node_type: str,
    name: Optional[str] = None,
    operation: Optional[str] = None,
) -> Dict[str, Any]:
    """Create one of the supported colour/utility nodes."""
    kind = str(node_type or "").strip()
    if kind not in UTILITY_NODES:
        raise CompositingContractError("Unsupported comp node {}. Supported: {}".format(kind, ", ".join(UTILITY_NODES)))
    node = cmds.createNode(kind, name=name) if name else cmds.createNode(kind)
    node = str(node)
    applied: Dict[str, Any] = {"node": node, "node_type": kind}
    if operation is not None:
        if kind != "multiplyDivide":
            raise CompositingContractError("operation only applies to multiplyDivide, not {}".format(kind))
        key = str(operation).strip().lower()
        if key not in MULTIPLY_DIVIDE_OPS:
            raise CompositingContractError(
                "Unknown operation {}. Supported: {}".format(operation, ", ".join(sorted(MULTIPLY_DIVIDE_OPS)))
            )
        cmds.setAttr("{}.operation".format(node), MULTIPLY_DIVIDE_OPS[key])
        applied["operation"] = key
    return applied


#: Candidate input plugs per node type, in preference order. Verified on Maya
#: 2025: ``multiplyDivide`` uses input1/input2, ``plusMinusAverage`` uses
#: input3D, and ``reverse`` / ``clamp`` use a plain ``input``.
INPUT_PLUGS: Dict[str, Tuple[str, ...]] = {
    "multiplyDivide": ("input1", "input2"),
    "plusMinusAverage": ("input3D",),
    "reverse": ("input",),
    "luminance": ("value",),
    "clamp": ("input",),
    "setRange": ("value",),
    "blendColors": ("color1", "color2"),
    "layeredTexture": ("inputs",),
    "file": (),  # a file node is a source, not a consumer
}


def connect_comp(cmds: Any, source: str, destination: str, source_attr: str = "outColor") -> Dict[str, Any]:
    """Connect two comp nodes together."""
    src = _resolve(cmds, source, "source")
    dst = _resolve(cmds, destination, "destination")
    src_plug = "{}.{}".format(src, str(source_attr or "").strip() or "outColor")
    if not cmds.objExists(src_plug):
        raise CompositingContractError("Source plug does not exist: {}".format(src_plug))

    dst_type = str(cmds.nodeType(dst))
    candidates = INPUT_PLUGS.get(dst_type)
    if candidates is None:
        raise CompositingContractError(
            "Unsupported destination type {}. Supported: {}".format(dst_type, ", ".join(sorted(INPUT_PLUGS)))
        )
    if not candidates:
        raise CompositingContractError("{} is a {} and has no colour input to connect into.".format(dst, dst_type))

    for attr in candidates:
        plug = "{}.{}".format(dst, attr)
        if not cmds.objExists(plug):
            continue
        if cmds.listConnections(plug, source=True, destination=False):
            continue
        cmds.connectAttr(src_plug, plug)
        return {"source": src_plug, "destination": plug}
    raise CompositingContractError(
        "{} ({}) has no free input among {}; all are already connected.".format(dst, dst_type, ", ".join(candidates))
    )
