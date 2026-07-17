"""Small, typed boundary around Maya's Bifrost VNN commands.

The functions in this module accept a ``maya.cmds``-compatible object so the
graph contract can be unit tested without importing Maya.  Skill entry points
remain responsible for lazy host imports and result-envelope handling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

BIFROST_GRAPH_TYPES: Tuple[str, ...] = ("bifrostGraphShape", "bifrostBoard")
BIFROST_PLUGINS: Tuple[str, ...] = ("mayaVnnPlugin", "bifrostGraph")


class BifrostContractError(ValueError):
    """Raised when a requested Bifrost graph operation is malformed."""


def _plugin_loaded(cmds: Any, plugin: str) -> bool:
    try:
        return bool(cmds.pluginInfo(plugin, query=True, loaded=True))
    except Exception:  # noqa: BLE001 - Maya raises for unknown plug-ins
        return False


def ensure_bifrost_plugins(cmds: Any) -> Dict[str, Any]:
    """Load the VNN and Bifrost graph plug-ins and return runtime metadata."""
    loaded_now: List[str] = []
    for plugin in BIFROST_PLUGINS:
        if _plugin_loaded(cmds, plugin):
            continue
        result = cmds.loadPlugin(plugin, quiet=True) or []
        if isinstance(result, (list, tuple)):
            loaded_now.extend(str(item) for item in result)
        else:
            loaded_now.append(str(result))
    version = None
    try:
        version = str(cmds.pluginInfo("bifrostGraph", query=True, version=True))
    except Exception:  # noqa: BLE001 - version metadata is diagnostic only
        pass
    return {
        "plugins": list(BIFROST_PLUGINS),
        "loaded_now": loaded_now,
        "bifrost_version": version,
    }


def require_graph(cmds: Any, graph: str) -> str:
    """Validate and return a Bifrost graph node name."""
    graph_name = str(graph or "").strip()
    if not graph_name:
        raise BifrostContractError("graph must be a non-empty Maya node name")
    if not cmds.objExists(graph_name):
        raise BifrostContractError("Bifrost graph does not exist: {}".format(graph_name))
    node_type = str(cmds.nodeType(graph_name))
    if node_type not in BIFROST_GRAPH_TYPES:
        raise BifrostContractError(
            "{} is a {}, expected one of {}".format(graph_name, node_type, ", ".join(BIFROST_GRAPH_TYPES))
        )
    return graph_name


def normalize_compound_path(compound: Optional[str]) -> str:
    """Return a VNN compound path, defaulting to the root compound."""
    value = str(compound or ".").strip()
    if value in ("", "/"):
        return "."
    if not value.startswith((".", "/")):
        value = "/" + value
    return value


def normalize_port_path(port: str) -> str:
    """Return an absolute-from-root VNN port path."""
    value = str(port or "").strip()
    if not value or "." not in value.lstrip("./"):
        raise BifrostContractError("port must include a node and port name, for example '.cube.cube_mesh'")
    if not value.startswith((".", "/")):
        value = "." + value
    return value


def split_node_type(node_type: str) -> Tuple[str, str]:
    """Split ``Modeling::Primitive::create_mesh_cube`` into library and name."""
    value = str(node_type or "").strip()
    if "::" not in value:
        raise BifrostContractError(
            "node_type must include its Bifrost library, for example 'Modeling::Primitive::create_mesh_cube'"
        )
    library, short_name = value.rsplit("::", 1)
    if not library or not short_name:
        raise BifrostContractError("node_type contains an empty library or node name")
    return library, short_name


def add_node(
    cmds: Any,
    graph: str,
    node_type: str,
    name: Optional[str] = None,
    compound: Optional[str] = None,
) -> str:
    """Add a typed Bifrost node and return its graph-local name."""
    graph_name = require_graph(cmds, graph)
    library, short_name = split_node_type(node_type)
    compound_path = normalize_compound_path(compound)
    created = (
        cmds.vnnCompound(
            graph_name,
            compound_path,
            addNode="BifrostGraph,{0},{1}".format(library, short_name),
        )
        or []
    )
    if not created:
        raise RuntimeError("Bifrost did not return a created node")
    node_name = str(created[-1])
    requested_name = str(name or "").strip()
    if requested_name and requested_name != node_name:
        renamed = cmds.vnnCompound(
            graph_name,
            compound_path,
            renameNode=(node_name, requested_name),
        )
        if isinstance(renamed, (list, tuple)) and renamed:
            node_name = str(renamed[-1])
        else:
            node_name = requested_name
    return node_name


def compound_node_path(compound: Optional[str], node: str) -> str:
    """Join a compound and local node name into a VNN node path."""
    compound_path = normalize_compound_path(compound)
    local_name = str(node or "").strip().lstrip("./")
    if not local_name:
        raise BifrostContractError("node must be a non-empty Bifrost node name")
    if compound_path == ".":
        return "." + local_name
    return compound_path.rstrip("/") + "/" + local_name


def encode_default_value(value: Any, nested: bool = False) -> str:
    """Encode JSON-compatible values for ``vnnNode -setPortDefaultValues``."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "{" + ", ".join(encode_default_value(item, nested=True) for item in value) + "}"
    if value is None:
        return ""
    text = str(value)
    if nested:
        return "'{}'".format(text.replace("\\", "\\\\").replace("'", "\\'"))
    return text


def node_path(node: str) -> str:
    """Normalize a node name into a VNN path."""
    value = str(node or "").strip()
    if not value:
        raise BifrostContractError("node must be a non-empty Bifrost node path")
    if not value.startswith((".", "/")):
        value = "." + value
    return value


def list_graphs(cmds: Any, include_nodes: bool = True, include_ports: bool = False) -> List[Dict[str, Any]]:
    """Return Bifrost graph and optional node/port metadata."""
    graphs: List[Dict[str, Any]] = []
    for graph_type in BIFROST_GRAPH_TYPES:
        for graph in cmds.ls(type=graph_type, long=True) or []:
            graph_name = str(graph)
            record: Dict[str, Any] = {
                "graph": graph_name,
                "node_type": graph_type,
            }
            parents = cmds.listRelatives(graph_name, parent=True, fullPath=True) or []
            if parents:
                record["transform"] = str(parents[0])
            if include_nodes:
                nodes = [str(item) for item in (cmds.vnnCompound(graph_name, ".", listNodes=True) or [])]
                record["nodes"] = nodes
                record["node_count"] = len(nodes)
                if include_ports:
                    record["ports"] = {
                        name: [str(port) for port in (cmds.vnnNode(graph_name, node_path(name), listPorts=True) or [])]
                        for name in nodes
                    }
            graphs.append(record)
    return graphs


def create_graph(cmds: Any, name: Optional[str] = None, kind: str = "graph_shape") -> Dict[str, Any]:
    """Create a Bifrost graph shape or board and return its Maya identities."""
    node_types = {"graph_shape": "bifrostGraphShape", "board": "bifrostBoard"}
    if kind not in node_types:
        raise BifrostContractError("kind must be one of: {}".format(", ".join(sorted(node_types))))
    kwargs = {}
    requested_name = str(name or "").strip()
    if requested_name:
        kwargs["name"] = requested_name
    graph = str(cmds.createNode(node_types[kind], **kwargs))
    parents = cmds.listRelatives(graph, parent=True, fullPath=True) or []
    if kind == "graph_shape":
        cmds.setAttr("{}.displayFinalInViewport".format(graph), True)
        try:
            cmds.sets(graph, edit=True, forceElement="initialShadingGroup")
        except Exception:  # noqa: BLE001 - shading assignment is best-effort in batch mode
            pass
    return {
        "graph": graph,
        "node_type": node_types[kind],
        "kind": kind,
        "transform": str(parents[0]) if parents else None,
    }


def connect_ports(
    cmds: Any,
    graph: str,
    source_port: str,
    destination_port: str,
    disconnect: bool = False,
    copy_metadata: bool = False,
) -> Dict[str, Any]:
    """Connect or disconnect two ports in a Bifrost graph."""
    graph_name = require_graph(cmds, graph)
    source = normalize_port_path(source_port)
    destination = normalize_port_path(destination_port)
    cmds.vnnConnect(
        graph_name,
        source,
        destination,
        disconnect=bool(disconnect),
        copyMetaData=bool(copy_metadata),
    )
    return {
        "graph": graph_name,
        "source_port": source,
        "destination_port": destination,
        "disconnected": bool(disconnect),
    }


def create_port(
    cmds: Any,
    graph: str,
    node: str,
    port: str,
    data_type: str,
    direction: str = "input",
) -> Dict[str, Any]:
    """Create a dynamic input or output port on a compatible Bifrost node."""
    graph_name = require_graph(cmds, graph)
    port_name = str(port or "").strip()
    type_name = str(data_type or "").strip()
    if not port_name or "." in port_name:
        raise BifrostContractError("port must be a local port name without dots")
    if not type_name:
        raise BifrostContractError("data_type must be a non-empty Bifrost type")
    if direction not in ("input", "output"):
        raise BifrostContractError("direction must be 'input' or 'output'")
    legacy_type_name = {
        "Object": "Amino::Object",
        "array<Object>": "array<Amino::Object>",
    }.get(type_name, type_name)
    flag = "createInputPort" if direction == "input" else "createOutputPort"
    path = node_path(node)
    cmds.vnnNode(graph_name, path, **{flag: (port_name, type_name)})
    if legacy_type_name != type_name:
        ports = [str(value).rsplit(".", 1)[-1] for value in (cmds.vnnNode(graph_name, path, listPorts=True) or [])]
        if port_name not in ports:
            cmds.vnnNode(graph_name, path, **{flag: (port_name, legacy_type_name)})
    return {
        "graph": graph_name,
        "node": node_path(node),
        "port": port_name,
        "data_type": type_name,
        "direction": direction,
    }


def set_port_default(cmds: Any, graph: str, node: str, port: str, value: Any) -> Dict[str, Any]:
    """Set an unconnected Bifrost node port's default value."""
    graph_name = require_graph(cmds, graph)
    port_name = str(port or "").strip()
    if not port_name or "." in port_name:
        raise BifrostContractError("port must be a local port name without dots")
    encoded = encode_default_value(value)
    path = node_path(node)
    cmds.vnnNode(graph_name, path, setPortDefaultValues=(port_name, encoded))
    return {
        "graph": graph_name,
        "node": path,
        "port": port_name,
        "value": value,
        "encoded_value": encoded,
    }
