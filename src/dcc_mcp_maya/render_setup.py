"""Small, typed boundary around Maya's render setup and AOV commands.

The functions accept a ``maya.cmds``-compatible object so the contract can be
unit tested without importing Maya.  Skill entry points remain responsible for
lazy host imports and result-envelope handling.

Three distinct Maya surfaces are covered, and they are deliberately **not**
merged because they behave differently:

* **renderSetup** (``maya.app.renderSetup.model.renderSetup``) — the modern
  layer system: layers, collections, overrides. This is the default for new
  work and the only one verified to switch correctly.
* **legacy render layers** (``cmds.createRenderLayer`` /
  ``cmds.editRenderLayerGlobals``) — the pre-2017 ``renderLayer`` nodes. Kept
  for reading and for scenes that still use them. Switching a legacy layer
  does not take effect in a batch session, so it is reported as such rather
  than silently appearing to succeed.
* **AOVs** — Arnold's ``aiAOV`` nodes wired into
  ``defaultArnoldRenderOptions.aovList``. Arnold may not be loaded, so every
  entry point fails closed with an actionable message instead of no-op'ing.

Verified against Maya 2025. Two behaviours are worth knowing because they are
easy to get wrong and invisible under a mock:

* ``defaultArnoldRenderOptions`` does **not** exist until an ``aiOptions`` node
  is created (merely setting ``currentRenderer`` is not enough).
* ``aovList`` reports ``size == 0`` via ``getAttr(s=True)`` even when populated;
  the next free index must come from ``listConnections``.
"""

from __future__ import annotations

# Import built-in modules
import importlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

RENDER_SETUP_MODULE = "maya.app.renderSetup.model.renderSetup"
ARNOLD_PLUGIN = "mtoa"
ARNOLD_OPTIONS_NODE = "defaultArnoldRenderOptions"
AOV_NODE_TYPE = "aiAOV"
ARNOLD_OPTIONS_TYPE = "aiOptions"

#: Override flavours ``Collection`` supports.
OVERRIDE_TYPES: Tuple[str, ...] = ("absolute", "relative", "connection")

#: Collection selector types offered by the tool.
SELECTOR_TYPES: Tuple[str, ...] = ("static", "pattern")

#: Arnold ``aiAOV.type`` enum, read from ``attributeQuery(listEnum=True)``:
#: ``int=1:uint:bool:float:rgb:rgba:vector:vector2=9:pointer=11``.
AOV_TYPES: Dict[str, int] = {
    "int": 1,
    "uint": 2,
    "bool": 3,
    "float": 4,
    "rgb": 5,
    "rgba": 6,
    "vector": 7,
    "vector2": 9,
    "pointer": 11,
}

#: Minimum / maximum for ``aiAOV.type``, so an out-of-range value is rejected
#: here with a useful message rather than by ``setAttr``.
AOV_TYPE_MIN = 1
AOV_TYPE_MAX = 11

RENDER_SETUP_UNAVAILABLE_HINT = (
    "maya.app.renderSetup.model.renderSetup could not be imported; "
    "load the renderSetup plug-in (cmds.loadPlugin('renderSetup')) first."
)


class RenderSetupContractError(ValueError):
    """Raised when a render setup / AOV operation is malformed or unavailable."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def as_str_list(value: Any) -> List[str]:
    """Normalise a scalar / list tool argument into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [str(item) for item in value if str(item).strip()]


def _require(value: str, what: str) -> str:
    name = str(value or "").strip()
    if not name:
        raise RenderSetupContractError("{} must be a non-empty name".format(what))
    return name


def load_render_setup() -> Any:
    """Return the renderSetup singleton, failing closed when unavailable.

    Uses :func:`importlib.import_module` rather than ``__import__`` so the
    module can be substituted in tests by seeding ``sys.modules``.
    """
    try:
        module = importlib.import_module(RENDER_SETUP_MODULE)
    except Exception as exc:  # noqa: BLE001 - import failure is the report
        raise RenderSetupContractError(
            "Render setup is unavailable: {}. ".format(exc) + RENDER_SETUP_UNAVAILABLE_HINT
        ) from exc
    instance = module.instance()
    if instance is None:
        raise RenderSetupContractError("Render setup is unavailable: instance() returned None")
    return instance


# ---------------------------------------------------------------------------
# renderSetup layers
# ---------------------------------------------------------------------------


def _layer_record(layer: Any) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "name": str(layer.name()),
        "type": type(layer).__name__,
    }
    for attr, key in (
        ("isRenderable", "renderable"),
        ("isVisible", "visible"),
    ):
        method = getattr(layer, attr, None)
        if callable(method):
            try:
                record[key] = bool(method())
            except Exception:  # noqa: BLE001 - introspection must not fail the call
                record[key] = None
    collections = getattr(layer, "getCollections", None)
    if callable(collections):
        try:
            record["collections"] = [str(item.name()) for item in (collections() or [])]
        except Exception:  # noqa: BLE001 - same reason
            record["collections"] = []
    return record


def create_render_layer(
    render_setup: Any,
    name: str,
    renderable: bool = True,
    activate: bool = False,
) -> Dict[str, Any]:
    """Create a renderSetup layer."""
    layer_name = _require(name, "name")
    existing = {str(item.name()) for item in (render_setup.getRenderLayers() or [])}
    if layer_name in existing:
        raise RenderSetupContractError(
            "A render layer named {} already exists. Existing: {}".format(
                layer_name, ", ".join(sorted(existing)) or "(none)"
            )
        )
    layer = render_setup.createRenderLayer(layer_name)
    if layer is None:
        raise RenderSetupContractError("Maya did not create render layer {}".format(layer_name))
    layer.setRenderable(bool(renderable))
    if activate:
        layer.makeVisible()
    return {"layer": _layer_record(layer), "created": layer_name}


def list_render_layers(
    render_setup: Any,
    include_default: bool = True,
) -> Dict[str, Any]:
    """List renderSetup layers."""
    layers = [_layer_record(item) for item in (render_setup.getRenderLayers() or [])]
    default_layer = None
    try:
        default_layer = str(render_setup.getDefaultRenderLayer().name())
    except Exception:  # noqa: BLE001 - default layer is diagnostic only
        default_layer = None
    visible = None
    try:
        visible = str(render_setup.getVisibleRenderLayer().name())
    except Exception:  # noqa: BLE001 - same reason
        visible = None
    if not include_default and default_layer:
        layers = [item for item in layers if item["name"] != default_layer]
    return {
        "layers": layers,
        "default_layer": default_layer,
        "visible_layer": visible,
        "count": len(layers),
    }


def switch_render_layer(render_setup: Any, name: str) -> Dict[str, Any]:
    """Make a renderSetup layer the visible one."""
    layer_name = _require(name, "name")
    for layer in render_setup.getRenderLayers() or []:
        if str(layer.name()) == layer_name:
            render_setup.switchToLayer(layer)
            return {"layer": layer_name, "visible_layer": layer_name}
    default_layer = None
    try:
        default_layer = render_setup.getDefaultRenderLayer()
    except Exception:  # noqa: BLE001 - default layer may be unavailable
        default_layer = None
    if default_layer is not None and str(default_layer.name()) == layer_name:
        render_setup.switchToLayer(default_layer)
        return {"layer": layer_name, "visible_layer": layer_name}

    known = sorted(str(item.name()) for item in (render_setup.getRenderLayers() or []))
    if default_layer is not None:
        known.append(str(default_layer.name()))
    raise RenderSetupContractError(
        "No render layer named {}. Known layers: {}".format(layer_name, ", ".join(sorted(set(known))) or "(none)")
    )


# ---------------------------------------------------------------------------
# Collections and overrides
# ---------------------------------------------------------------------------


def _find_layer(render_setup: Any, name: str) -> Any:
    layer_name = _require(name, "layer")
    for layer in render_setup.getRenderLayers() or []:
        if str(layer.name()) == layer_name:
            return layer
    known = sorted(str(item.name()) for item in (render_setup.getRenderLayers() or []))
    raise RenderSetupContractError(
        "No render layer named {}. Known layers: {}".format(layer_name, ", ".join(known) or "(none)")
    )


def create_collection(
    render_setup: Any,
    layer: str,
    name: str,
    members: Optional[Sequence[str]] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a collection inside a renderSetup layer and populate it."""
    target = _find_layer(render_setup, layer)
    collection_name = _require(name, "name")
    if members and pattern:
        raise RenderSetupContractError("Pass either members or pattern, not both")
    if not members and not pattern:
        raise RenderSetupContractError("collection needs members or a pattern")

    existing = {str(item.name()) for item in (target.getCollections() or [])}
    if collection_name in existing:
        raise RenderSetupContractError(
            "Layer {} already has a collection named {}. Existing: {}".format(
                layer, collection_name, ", ".join(sorted(existing))
            )
        )
    collection = target.createCollection(collection_name)
    if collection is None:
        raise RenderSetupContractError("Maya did not create collection {}".format(collection_name))

    selector = collection.getSelector()
    requested: List[str] = []
    if members:
        requested = as_str_list(members)
        if not requested:
            raise RenderSetupContractError("members must name at least one node")
        selector.setStaticSelection(requested)
    else:
        selector.setPattern(str(pattern))
    return {
        "layer": str(target.name()),
        "collection": collection_name,
        "selector_type": "static" if members else "pattern",
        "requested": requested,
        "pattern": str(pattern) if pattern else None,
    }


def set_collection_members(
    render_setup: Any,
    layer: str,
    collection: str,
    members: Optional[Sequence[str]] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    """Replace a collection's selector contents."""
    target = _find_layer(render_setup, layer)
    collection_name = _require(collection, "collection")
    if members and pattern:
        raise RenderSetupContractError("Pass either members or pattern, not both")
    if members is not None and pattern is None and not as_str_list(members):
        raise RenderSetupContractError("members must name at least one node")
    if members is None and not pattern:
        raise RenderSetupContractError("Provide members or pattern to set")

    found = None
    for item in target.getCollections() or []:
        if str(item.name()) == collection_name:
            found = item
            break
    if found is None:
        known = sorted(str(item.name()) for item in (target.getCollections() or []))
        raise RenderSetupContractError(
            "Layer {} has no collection named {}. Existing: {}".format(
                layer, collection_name, ", ".join(known) or "(none)"
            )
        )

    selector = found.getSelector()
    requested: List[str] = []
    if members:
        requested = as_str_list(members)
        if not requested:
            raise RenderSetupContractError("members must name at least one node")
        selector.setStaticSelection(requested)
    else:
        selector.setPattern(str(pattern))
    return {
        "layer": str(target.name()),
        "collection": collection_name,
        "selector_type": "static" if members else "pattern",
        "requested": requested,
        "pattern": str(pattern) if pattern else None,
    }


def create_override(
    render_setup: Any,
    layer: str,
    collection: str,
    attribute: str,
    value: Any = None,
    override_type: str = "absolute",
) -> Dict[str, Any]:
    """Create an override on a collection for ``node.attribute``."""
    target = _find_layer(render_setup, layer)
    collection_name = _require(collection, "collection")
    attr_name = _require(attribute, "attribute")
    kind = str(override_type or "absolute").strip().lower()
    if kind not in OVERRIDE_TYPES:
        raise RenderSetupContractError("override_type must be one of: {}".format(", ".join(OVERRIDE_TYPES)))
    if kind != "connection" and value is None:
        raise RenderSetupContractError("value is required for a {} override".format(kind))

    found = None
    for item in target.getCollections() or []:
        if str(item.name()) == collection_name:
            found = item
            break
    if found is None:
        known = sorted(str(item.name()) for item in (target.getCollections() or []))
        raise RenderSetupContractError(
            "Layer {} has no collection named {}. Existing: {}".format(
                layer, collection_name, ", ".join(known) or "(none)"
            )
        )

    # ``attribute`` may be "node.attr" or a bare attribute for every member.
    node_name, _, bare_attr = attr_name.rpartition(".")
    factory_name = {
        "absolute": "createAbsoluteOverride",
        "relative": "createRelativeOverride",
        "connection": "createConnectionOverride",
    }[kind]
    factory = getattr(found, factory_name, None)
    if factory is None or not callable(factory):
        raise RenderSetupContractError("This Maya build does not support {} overrides ({})".format(kind, factory_name))

    applied: Dict[str, Any] = {"override_type": kind, "attribute": attr_name}
    try:
        if kind == "connection":
            override = factory(attr_name, str(value))
        elif node_name:
            override = factory(node_name, bare_attr)
            override.setAttrValue(value)
        else:
            override = factory(attr_name)
            override.setAttrValue(value)
    except Exception as exc:  # noqa: BLE001 - surface Maya's reason verbatim
        raise RenderSetupContractError("Could not create {} override on {}: {}".format(kind, attr_name, exc)) from exc

    applied["override"] = str(override.name())
    applied["value"] = None if kind == "connection" else str(value)
    return {
        "layer": str(target.name()),
        "collection": collection_name,
        **applied,
    }


# ---------------------------------------------------------------------------
# Legacy render layers
# ---------------------------------------------------------------------------


def list_legacy_render_layers(cmds: Any) -> Dict[str, Any]:
    """List legacy ``renderLayer`` nodes."""
    layers: List[Dict[str, Any]] = []
    for node in sorted(str(item) for item in (cmds.ls(type="renderLayer") or [])):
        record: Dict[str, Any] = {"name": node}
        for attr in ("renderable", "visible"):
            plug = "{}.{}".format(node, attr)
            try:
                record[attr] = bool(cmds.getAttr(plug)) if cmds.objExists(plug) else None
            except Exception:  # noqa: BLE001 - introspection must not fail the call
                record[attr] = None
        layers.append(record)
    current = None
    try:
        current = str(cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True))
    except Exception:  # noqa: BLE001 - legacy globals may be absent
        current = None
    return {"layers": layers, "current": current, "count": len(layers)}


def switch_legacy_render_layer(cmds: Any, name: str) -> Dict[str, Any]:
    """Switch the legacy render layer, reporting whether it actually took."""
    layer_name = _require(name, "name")
    known = sorted(str(item) for item in (cmds.ls(type="renderLayer") or []))
    if layer_name not in known:
        raise RenderSetupContractError(
            "No legacy render layer named {}. Known layers: {}".format(layer_name, ", ".join(known) or "(none)")
        )
    cmds.editRenderLayerGlobals(currentRenderLayer=layer_name)
    applied = None
    try:
        applied = str(cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True))
    except Exception:  # noqa: BLE001 - readback is diagnostic only
        applied = None
    # Maya silently ignores the switch in batch sessions; say so instead of
    # reporting a success that did not happen (batch-1 lesson: no silent no-op).
    return {
        "requested": layer_name,
        "current": applied,
        "applied": applied == layer_name,
    }


# ---------------------------------------------------------------------------
# AOVs (Arnold)
# ---------------------------------------------------------------------------


def ensure_arnold(cmds: Any) -> Dict[str, Any]:
    """Load Arnold and guarantee ``defaultArnoldRenderOptions`` exists."""
    try:
        loaded = bool(cmds.pluginInfo(ARNOLD_PLUGIN, query=True, loaded=True))
    except Exception:  # noqa: BLE001 - pluginInfo may reject an unknown name
        loaded = False
    if not loaded:
        try:
            cmds.loadPlugin(ARNOLD_PLUGIN, quiet=True)
            loaded = bool(cmds.pluginInfo(ARNOLD_PLUGIN, query=True, loaded=True))
        except Exception as exc:  # noqa: BLE001 - report the real reason
            raise RenderSetupContractError(
                "Arnold (mtoa) could not be loaded: {}. AOVs are only available "
                "with Arnold; install/enable mtoa or switch renderer.".format(exc)
            ) from exc
    if not loaded:
        raise RenderSetupContractError(
            "Arnold (mtoa) is not loaded, so AOVs are unavailable. "
            "Enable the mtoa plug-in, or use a renderer-agnostic workflow."
        )

    # Setting currentRenderer is NOT enough - the aiOptions node must exist.
    if not cmds.objExists(ARNOLD_OPTIONS_NODE):
        try:
            cmds.createNode(ARNOLD_OPTIONS_TYPE, name=ARNOLD_OPTIONS_NODE)
        except Exception as exc:  # noqa: BLE001 - report the real reason
            raise RenderSetupContractError(
                "Arnold is loaded but {} could not be created: {}. Open the Render "
                "Settings window once to initialise Arnold render options.".format(ARNOLD_OPTIONS_NODE, exc)
            ) from exc
    return {"plugin": ARNOLD_PLUGIN, "options_node": ARNOLD_OPTIONS_NODE, "loaded": True}


def _aov_index(cmds: Any) -> int:
    """Next free ``aovList`` index.

    ``getAttr(node.aovList, size=True)`` reports 0 even when the array is
    populated, so the count must come from ``listConnections``.
    """
    return len(cmds.listConnections(_aov_list_plug(), source=True, destination=False) or [])


def _aov_list_plug() -> str:
    return "{}.aovList".format(ARNOLD_OPTIONS_NODE)


def _aov_record(cmds: Any, node: str) -> Dict[str, Any]:
    record: Dict[str, Any] = {"node": str(node)}
    for attr in ("name", "type", "enabled"):
        plug = "{}.{}".format(node, attr)
        try:
            record[attr] = cmds.getAttr(plug) if cmds.objExists(plug) else None
        except Exception:  # noqa: BLE001 - introspection must not fail the call
            record[attr] = None
    return record


def resolve_aov_type(aov_type: Any) -> int:
    """Resolve a named or numeric AOV type to its ``aiAOV.type`` value."""
    if aov_type is None:
        return AOV_TYPES["rgba"]
    if isinstance(aov_type, int) and not isinstance(aov_type, bool):
        value = aov_type
    else:
        key = str(aov_type).strip().lower()
        if key not in AOV_TYPES:
            raise RenderSetupContractError(
                "Unknown AOV type {}. Supported: {}".format(aov_type, ", ".join(sorted(AOV_TYPES)))
            )
        value = AOV_TYPES[key]
    if not AOV_TYPE_MIN <= value <= AOV_TYPE_MAX:
        raise RenderSetupContractError(
            "AOV type {} is outside the supported range {}..{}".format(value, AOV_TYPE_MIN, AOV_TYPE_MAX)
        )
    return value


def add_aov(
    cmds: Any,
    name: str,
    aov_type: Any = None,
    node_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an Arnold AOV and wire it into ``aovList``."""
    aov_name = _require(name, "name")
    value = resolve_aov_type(aov_type)
    ensure_arnold(cmds)

    existing = {record["name"] for record in list_aovs(cmds)["aovs"]}
    if aov_name in existing:
        raise RenderSetupContractError(
            "An AOV named {} already exists. Existing: {}".format(
                aov_name, ", ".join(sorted(str(item) for item in existing)) or "(none)"
            )
        )

    node = str(node_name or "").strip() or "{}_{}".format(AOV_NODE_TYPE, aov_name)
    created = cmds.createNode(AOV_NODE_TYPE, name=node)
    node = str(created)
    cmds.setAttr("{}.name".format(node), aov_name, type="string")
    cmds.setAttr("{}.type".format(node), value)

    index = _aov_index(cmds)
    cmds.connectAttr(
        "{}.message".format(node),
        "{}[{}]".format(_aov_list_plug(), index),
        force=True,
    )
    return {
        "aov": _aov_record(cmds, node),
        "index": index,
        "duplicated_name": created != node,
    }


def list_aovs(cmds: Any) -> Dict[str, Any]:
    """List the AOVs wired into Arnold's ``aovList``."""
    ensure_arnold(cmds)
    nodes = cmds.listConnections(_aov_list_plug(), source=True, destination=False) or []
    aovs = [_aov_record(cmds, str(node)) for node in nodes]
    return {"aovs": aovs, "count": len(aovs), "options_node": ARNOLD_OPTIONS_NODE}


def _resolve_aov_node(cmds: Any, aov: str) -> str:
    target = _require(aov, "aov")
    ensure_arnold(cmds)
    nodes = [str(item) for item in (cmds.listConnections(_aov_list_plug(), source=True, destination=False) or [])]
    for node in nodes:
        plug = "{}.name".format(node)
        try:
            if cmds.objExists(plug) and str(cmds.getAttr(plug)) == target:
                return node
        except Exception:  # noqa: BLE001 - keep scanning
            continue
    if target in nodes:
        return target
    known = []
    for node in nodes:
        try:
            known.append("{}({})".format(node, cmds.getAttr("{}.name".format(node))))
        except Exception:  # noqa: BLE001 - diagnostic only
            known.append(node)
    raise RenderSetupContractError("No AOV named {}. Current AOVs: {}".format(target, ", ".join(known) or "(none)"))


def set_aov_enabled(cmds: Any, aov: str, enabled: bool) -> Dict[str, Any]:
    """Enable or disable an existing AOV without disconnecting it."""
    node = _resolve_aov_node(cmds, aov)
    cmds.setAttr("{}.enabled".format(node), bool(enabled))
    return {"aov": _aov_record(cmds, node), "enabled": bool(enabled)}


def remove_aov(cmds: Any, aov: str) -> Dict[str, Any]:
    """Disconnect and delete an AOV, keeping the array compact."""
    node = _resolve_aov_node(cmds, aov)
    record = _aov_record(cmds, node)
    index = _aov_index(cmds)
    for slot in range(index):
        plug = "{}[{}]".format(_aov_list_plug(), slot)
        try:
            sources = cmds.listConnections(plug, source=True, destination=False) or []
        except Exception:  # noqa: BLE001 - an empty slot can fail to query
            sources = []
        if node in [str(item) for item in sources]:
            cmds.disconnectAttr("{}.message".format(node), plug)
            break
    cmds.delete(node)
    return {"removed": record, "remaining": list_aovs(cmds)["count"]}


# ---------------------------------------------------------------------------
# Precomp helpers (pure - never touches Maya)
# ---------------------------------------------------------------------------


def build_output_paths(
    directory: str,
    layers: Optional[Sequence[str]] = None,
    aovs: Optional[Sequence[str]] = None,
    file_name: str = "<Scene>",
    start_frame: int = 1,
    end_frame: int = 1,
    frame_padding: int = 4,
    extension: str = "exr",
    separate_aov_folders: bool = True,
    separate_layer_folders: bool = True,
) -> Dict[str, Any]:
    """Compose per-layer / per-AOV output paths for a compositing hand-off.

    Pure string composition: it never touches Maya, so it is safe to call for
    planning before anything is rendered, and easy to unit test.
    """
    root = str(directory or "").strip()
    if not root:
        raise RenderSetupContractError("directory is required to build output paths")
    if frame_padding < 1:
        raise RenderSetupContractError("frame_padding must be >= 1, got {}".format(frame_padding))
    try:
        start = int(start_frame)
        end = int(end_frame)
    except (TypeError, ValueError) as exc:
        raise RenderSetupContractError("start_frame / end_frame must be integers") from exc
    if end < start:
        raise RenderSetupContractError("end_frame ({}) must be >= start_frame ({})".format(end, start))

    layer_names = as_str_list(layers) or [""]
    aov_names = as_str_list(aovs) or [""]
    extension = str(extension or "").strip().lstrip(".") or "exr"
    base = str(file_name or "").strip() or "<Scene>"

    import os

    outputs: List[Dict[str, Any]] = []
    for layer_name in layer_names:
        for aov_name in aov_names:
            parts: List[str] = [root]
            if separate_layer_folders and layer_name:
                parts.append(layer_name)
            if separate_aov_folders and aov_name:
                parts.append(aov_name)
            folder = os.path.join(*parts)
            segments = [base]
            if layer_name:
                segments.append(layer_name)
            if aov_name:
                segments.append(aov_name)
            outputs.append(
                {
                    "layer": layer_name or None,
                    "aov": aov_name or None,
                    "directory": folder,
                    "pattern": "{}.{}.{}".format(
                        "_".join(segments),
                        "#" * int(frame_padding),
                        extension,
                    ),
                    "frame_range": [start, end],
                    "frame_count": end - start + 1,
                }
            )
    return {
        "directory": root,
        "outputs": outputs,
        "count": len(outputs),
        "frame_range": [start, end],
        "frame_padding": int(frame_padding),
        "extension": extension,
    }
