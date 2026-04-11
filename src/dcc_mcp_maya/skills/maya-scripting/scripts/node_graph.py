"""Maya node graph / hypergraph actions.

Provides attribute-connection operations and DAG path queries that let
an Agent manipulate the Maya node network directly.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def connect_attr(
    source_attr: str,
    dest_attr: str,
    force: bool = False,
) -> dict:
    """Connect two Maya node attributes.

    Args:
        source_attr: Full attribute path of the driver, e.g.
            ``"pSphere1.translateX"``.
        dest_attr: Full attribute path of the driven attribute.
        force: If True, break any existing connection on *dest_attr* before
            connecting.  Default: False.

    Returns:
        ActionResultModel dict with ``context.source_attr`` and
        ``context.dest_attr``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source_attr):
            return maya_error(
                "Source attribute not found: {}".format(source_attr),
                "'{}' does not exist".format(source_attr),
            )

        if not cmds.objExists(dest_attr):
            return maya_error(
                "Destination attribute not found: {}".format(dest_attr),
                "'{}' does not exist".format(dest_attr),
            )

        cmds.connectAttr(source_attr, dest_attr, force=force)

        return maya_success(
            "Connected {} -> {}".format(source_attr, dest_attr),
            source_attr=source_attr,
            dest_attr=dest_attr,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error(
            "Failed to connect {} -> {}".format(source_attr, dest_attr),
            str(exc),
        )


def disconnect_attr(
    source_attr: str,
    dest_attr: str,
) -> dict:
    """Disconnect two connected Maya node attributes.

    Args:
        source_attr: Full attribute path of the driver, e.g.
            ``"pSphere1.translateX"``.
        dest_attr: Full attribute path of the driven attribute.

    Returns:
        ActionResultModel dict with ``context.source_attr`` and
        ``context.dest_attr``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source_attr):
            return maya_error(
                "Source attribute not found: {}".format(source_attr),
                "'{}' does not exist".format(source_attr),
            )

        if not cmds.objExists(dest_attr):
            return maya_error(
                "Destination attribute not found: {}".format(dest_attr),
                "'{}' does not exist".format(dest_attr),
            )

        # Check if actually connected before attempting disconnect
        if not cmds.isConnected(source_attr, dest_attr):
            return maya_error(
                "Attributes not connected: {} -> {}".format(source_attr, dest_attr),
                "No connection exists between these attributes",
            )

        cmds.disconnectAttr(source_attr, dest_attr)

        return maya_success(
            "Disconnected {} -x-> {}".format(source_attr, dest_attr),
            source_attr=source_attr,
            dest_attr=dest_attr,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error(
            "Failed to disconnect {} -> {}".format(source_attr, dest_attr),
            str(exc),
        )


def list_connections(
    object_name: str,
    attribute: Optional[str] = None,
    incoming: bool = True,
    outgoing: bool = True,
) -> dict:
    """List nodes/attributes connected to a Maya node or attribute.

    Args:
        object_name: Name of the Maya node to inspect.
        attribute: If specified, inspect connections on this specific
            attribute (e.g. ``"translateX"``).  If None, inspect all
            connections on the node.
        incoming: Include incoming connections.  Default: True.
        outgoing: Include outgoing connections.  Default: True.

    Returns:
        ActionResultModel dict with ``context.connections`` — a list of
        connected attribute path strings, and ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        query_target = "{}.{}".format(object_name, attribute) if attribute else object_name
        if attribute and not cmds.objExists(query_target):
            return maya_error(
                "Attribute not found: {}".format(query_target),
                "The attribute '{}' does not exist on '{}'".format(attribute, object_name),
            )

        connections = (
            cmds.listConnections(
                query_target,
                source=incoming,
                destination=outgoing,
                plugs=True,
                connections=True,
            )
            or []
        )

        # listConnections returns alternating pairs [src, dst, src, dst, ...]
        # Flatten into a list of connection dicts
        pairs = []
        it = iter(connections)
        for a, b in zip(it, it):
            pairs.append({"from": a, "to": b})

        return maya_success(
            "Found {} connection(s) on '{}'".format(len(pairs), query_target),
            object_name=object_name,
            attribute=attribute,
            connections=pairs,
            count=len(pairs),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list connections on {}".format(object_name))


def get_dag_path(
    object_name: str,
) -> dict:
    """Return the full DAG path of a Maya node.

    Resolves the shortest unique path for the given node name, then returns
    its full absolute DAG path (e.g. ``"|group1|pSphere1"``).

    Args:
        object_name: Short or partial name of the node.

    Returns:
        ActionResultModel dict with ``context.dag_path`` (full path),
        ``context.short_name``, and ``context.node_type``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        # ls -long returns full DAG paths
        full_paths = cmds.ls(object_name, long=True)
        if not full_paths:
            return maya_error(
                "Could not resolve DAG path for: {}".format(object_name),
                "cmds.ls returned empty list",
            )

        dag_path = full_paths[0]
        node_type = cmds.objectType(object_name)
        short_name = dag_path.split("|")[-1]

        return maya_success(
            "DAG path for '{}': {}".format(object_name, dag_path),
            dag_path=dag_path,
            short_name=short_name,
            node_type=node_type,
            object_name=object_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get DAG path for {}".format(object_name))


def smooth_mesh(
    object_name: str,
    divisions: int = 1,
    method: str = "preview",
) -> dict:
    """Apply smooth mesh preview or subdivision to a polygon mesh.

    Two methods are supported:

    * ``"preview"`` – activates Maya's Smooth Mesh Preview
      (``displaySmoothMesh`` attribute, non-destructive).
    * ``"subdivide"`` – applies ``cmds.polySmooth`` to subdivide the mesh
      destructively.

    Args:
        object_name: Name of the polygon transform/mesh to smooth.
        divisions: Subdivision level.  For ``"preview"`` this sets the
            ``smoothLevel`` attribute.  For ``"subdivide"`` it is the number
            of subdivision iterations.  Default: 1.
        method: ``"preview"`` (default) or ``"subdivide"``.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.divisions``, ``context.method``.
    """

    _VALID_METHODS = ("preview", "subdivide")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if method not in _VALID_METHODS:
            return maya_error(
                "Invalid method: {}".format(method),
                "method must be one of {}".format(_VALID_METHODS),
            )

        if divisions < 0:
            return maya_error(
                "Invalid divisions: {}".format(divisions),
                "divisions must be >= 0",
            )

        if method == "preview":
            # Enable smooth mesh preview — attribute lives on the shape node
            shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True) or []
            target = shapes[0] if shapes else object_name
            cmds.setAttr("{}.displaySmoothMesh".format(target), 2)  # 2 = smooth + cage
            cmds.setAttr("{}.smoothLevel".format(target), divisions)
            return maya_success(
                "Enabled smooth mesh preview on '{}' (level {})".format(object_name, divisions),
                object_name=object_name,
                divisions=divisions,
                method=method,
                prompt="Check the result with list_scripting or use related actions to continue.",
            )

        # method == "subdivide"
        result = cmds.polySmooth(object_name, divisions=divisions)
        node_name = result[0] if result else "polySmoothFace1"
        return maya_success(
            "Subdivided '{}' with {} iteration(s)".format(object_name, divisions),
            object_name=object_name,
            divisions=divisions,
            method=method,
            poly_smooth_node=node_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to smooth mesh {}".format(object_name))


def list_history(
    object_name: str,
    future: bool = False,
    levels: int = 0,
) -> dict:
    """List construction history nodes for a Maya object.

    Args:
        object_name: Name of the Maya node to inspect.
        future: If True, include *downstream* (future) nodes in addition to
            upstream history.  Default: False.
        levels: Maximum number of levels to traverse.  ``0`` means unlimited.
            Default: 0.

    Returns:
        ActionResultModel dict with ``context.history`` — a list of dicts
        with ``name`` and ``type`` for each history node, and
        ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        kwargs = {
            "future": future,
            "levels": levels,
        }
        history_nodes = cmds.listHistory(object_name, **kwargs) or []

        history = [{"name": node, "type": cmds.objectType(node)} for node in history_nodes if node != object_name]

        return maya_success(
            "Found {} history node(s) for '{}'".format(len(history), object_name),
            object_name=object_name,
            history=history,
            count=len(history),
            future=future,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list history for {}".format(object_name))


def delete_history(
    object_name: str,
) -> dict:
    """Delete the construction history on a Maya object.

    Equivalent to *Edit > Delete by Type > History* in Maya.  Bakes the
    current deformed state into the mesh and removes all upstream history
    nodes, which can improve scene performance.

    Args:
        object_name: Name of the transform or shape node to process.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        cmds.delete(object_name, constructionHistory=True)

        return maya_success(
            "Deleted construction history on '{}'".format(object_name),
            object_name=object_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete history for {}".format(object_name))


def apply_symmetry(
    object_name: str,
    axis: str = "x",
    world_space: bool = True,
) -> dict:
    """Apply mesh symmetry to a polygon object using ``cmds.symmetricModelling``.

    This enables Maya's interactive Symmetry tool on the specified axis so
    that subsequent edits are mirrored automatically.  To disable symmetry,
    call with ``axis="none"``.

    Args:
        object_name: Name of the polygon mesh transform to apply symmetry on.
        axis: Symmetry axis – one of ``"x"``, ``"y"``, ``"z"``, ``"none"``.
            Default: ``"x"``.
        world_space: If True, symmetry is evaluated in world space; otherwise
            object space.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.axis``, ``context.world_space``.
    """

    _VALID_AXES = ("x", "y", "z", "none")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return maya_error(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            )

        if axis_lower == "none":
            cmds.symmetricModelling(symmetry=False)
        else:
            space = "world" if world_space else "object"
            cmds.symmetricModelling(
                object_name,
                symmetry=True,
                axis=axis_lower,
                about=space,
            )

        return maya_success(
            "Applied {} symmetry on '{}' ({} space)".format(
                axis_lower, object_name, "world" if world_space else "object"
            ),
            object_name=object_name,
            axis=axis_lower,
            world_space=world_space,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to apply symmetry on {}".format(object_name))


def transfer_attributes(
    source: str,
    target: str,
    sample_space: int = 0,
    transfer_positions: bool = False,
    transfer_normals: bool = True,
    transfer_uvs: bool = True,
    transfer_colors: bool = False,
) -> dict:
    """Transfer mesh attributes (UVs, normals, vertex colors) from one mesh to another.

    Uses ``cmds.transferAttributes`` to copy surface data between two polygon
    meshes that share a similar topology or surface shape.

    Args:
        source: Name of the *source* mesh (or its transform).
        target: Name of the *target* mesh (or its transform) that will
            receive the transferred data.
        sample_space: Space used for attribute sampling:
            ``0`` = World space (default), ``1`` = Local space,
            ``4`` = UV space, ``5`` = Component space.
        transfer_positions: If True, transfer vertex positions.
            Default: False.
        transfer_normals: If True, transfer vertex normals.  Default: True.
        transfer_uvs: If True, transfer UV sets.  Default: True.
        transfer_colors: If True, transfer vertex color sets.  Default: False.

    Returns:
        ActionResultModel dict with ``context.source``, ``context.target``,
        ``context.transfer_node`` (the created ``transferAttributes`` node).
    """

    _VALID_SPACES = (0, 1, 4, 5)

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source):
            return maya_error(
                "Source not found: {}".format(source),
                "'{}' does not exist in the scene".format(source),
            )

        if not cmds.objExists(target):
            return maya_error(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            )

        if sample_space not in _VALID_SPACES:
            return maya_error(
                "Invalid sample_space: {}".format(sample_space),
                "sample_space must be one of {} (0=World, 1=Local, 4=UV, 5=Component)".format(_VALID_SPACES),
            )

        result = cmds.transferAttributes(
            source,
            target,
            transferPositions=int(transfer_positions),
            transferNormals=int(transfer_normals),
            transferUVs=int(transfer_uvs),
            transferColors=int(transfer_colors),
            sampleSpace=sample_space,
        )
        node_name = result[0] if result else "transferAttributes1"

        return maya_success(
            "Transferred attributes from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            transfer_node=node_name,
            sample_space=sample_space,
            transfer_positions=transfer_positions,
            transfer_normals=transfer_normals,
            transfer_uvs=transfer_uvs,
            transfer_colors=transfer_colors,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error("Failed to transfer attributes from '{}' to '{}'".format(source, target), str(exc))
