"""Maya nDynamics: nucleus solver, dynamic fields, and simulation utilities."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def create_nucleus(
    name: Optional[str] = None,
    gravity: float = -9.8,
    wind_speed: float = 0.0,
    wind_direction: Optional[List[float]] = None,
) -> dict:
    """Create an nDynamics nucleus solver node.

    Args:
        name: Optional name for the nucleus node.  Maya auto-names if
            ``None``.
        gravity: Gravity magnitude (world units/sec²).  Negative value pulls
            downward (default ``-9.8``).
        wind_speed: Wind speed magnitude.  Default: ``0.0`` (no wind).
        wind_direction: ``[x, y, z]`` normalised wind direction vector.
            Defaults to ``[0, 0, 1]`` (positive Z) when not provided.

    Returns:
        ActionResultModel dict with ``context.nucleus_node``,
        ``context.gravity``, ``context.wind_speed``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    wind_dir = wind_direction if (wind_direction and len(wind_direction) == 3) else [0.0, 0.0, 1.0]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nucleus_kwargs = {}
        if name:
            nucleus_kwargs["name"] = name

        nucleus_node = cmds.createNode("nucleus", **nucleus_kwargs)

        # Configure gravity
        cmds.setAttr("{}.gravity".format(nucleus_node), gravity)

        # Configure wind
        cmds.setAttr("{}.windSpeed".format(nucleus_node), wind_speed)
        cmds.setAttr(
            "{}.windDirection".format(nucleus_node),
            wind_dir[0],
            wind_dir[1],
            wind_dir[2],
            type="double3",
        )

        # Connect to time node so the solver advances
        time_node = cmds.ls(type="time")[0] if cmds.ls(type="time") else "time1"
        if not cmds.isConnected("{}.outTime".format(time_node), "{}.currentTime".format(nucleus_node)):
            cmds.connectAttr("{}.outTime".format(time_node), "{}.currentTime".format(nucleus_node))

        return success_result(
            "Created nucleus solver '{}'".format(nucleus_node),
            nucleus_node=nucleus_node,
            gravity=gravity,
            wind_speed=wind_speed,
            wind_direction=wind_dir,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_nucleus failed")
        return error_result("Failed to create nucleus solver", str(exc)).to_dict()


def set_nucleus_attribute(
    nucleus: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute on a Maya nucleus solver node.

    Args:
        nucleus: Name of the nucleus node.
        attribute: Attribute name (e.g. ``"gravity"``, ``"windSpeed"``,
            ``"substeps"``, ``"maxCollisionIterations"``).
        value: Scalar value, or ``[x, y, z]`` list for triple attrs such as
            ``"windDirection"``.

    Returns:
        ActionResultModel dict with ``context.nucleus``,
        ``context.attribute``, ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(nucleus):
            return error_result(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            ).to_dict()

        node_type = cmds.objectType(nucleus)
        if node_type != "nucleus":
            return error_result(
                "Not a nucleus node: {}".format(nucleus),
                "Expected node type 'nucleus', got '{}'".format(node_type),
            ).to_dict()

        plug = "{}.{}".format(nucleus, attribute)
        if not cmds.objExists(plug):
            return error_result(
                "Attribute not found: {}".format(plug),
                "'{}' does not have attribute '{}'".format(nucleus, attribute),
            ).to_dict()

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(plug, value, type="string")
        else:
            cmds.setAttr(plug, value)

        return success_result(
            "Set '{}.{}' = {}".format(nucleus, attribute, value),
            nucleus=nucleus,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_nucleus_attribute failed")
        return error_result("Failed to set attribute on nucleus '{}'".format(nucleus), str(exc)).to_dict()


def create_dynamic_field(
    field_type: str = "gravity",
    name: Optional[str] = None,
    magnitude: float = 9.8,
    objects: Optional[List[str]] = None,
) -> dict:
    """Create a Maya dynamic field and optionally connect it to objects.

    Supported field types: ``gravity``, ``turbulence``, ``radial``,
    ``uniform``, ``vortex``, ``drag``, ``newton``, ``air``.

    Args:
        field_type: Type of dynamic field to create.  Default: ``"gravity"``.
        name: Optional name for the field node.  Maya auto-names if ``None``.
        magnitude: Field strength/magnitude.  Default: ``9.8``.
        objects: Optional list of particle/nParticle system names to connect
            the field to via ``cmds.connectDynamic(fields=...)``.

    Returns:
        ActionResultModel dict with ``context.field_node``,
        ``context.field_type``, ``context.magnitude``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    ft = field_type.lower()
    if ft not in _VALID_FIELD_TYPES:
        return error_result(
            "Invalid field type: {}".format(field_type),
            "Supported types: {}".format(", ".join(_VALID_FIELD_TYPES)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        create_fn = getattr(cmds, ft, None)
        if create_fn is None:
            return error_result(
                "Field type not available: {}".format(ft),
                "cmds.{} is not accessible in this Maya version".format(ft),
            ).to_dict()

        field_kwargs = {}
        if name:
            field_kwargs["name"] = name

        result = create_fn(**field_kwargs)
        field_node = result[0] if isinstance(result, (list, tuple)) else result

        # Set magnitude
        mag_attr = "{}.magnitude".format(field_node)
        if cmds.objExists(mag_attr):
            cmds.setAttr(mag_attr, magnitude)

        # Connect to particle systems
        connected = []
        if objects:
            missing = [o for o in objects if not cmds.objExists(o)]
            if missing:
                return error_result(
                    "Object(s) not found: {}".format(", ".join(missing)),
                    "Ensure all objects exist before connecting the field",
                ).to_dict()
            cmds.connectDynamic(objects, fields=field_node)
            connected = list(objects)

        return success_result(
            "Created {} field '{}'".format(ft, field_node),
            field_node=field_node,
            field_type=ft,
            magnitude=magnitude,
            connected_objects=connected,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_dynamic_field failed")
        return error_result("Failed to create dynamic field", str(exc)).to_dict()


def connect_field_to_objects(
    field_node: str,
    objects: List[str],
) -> dict:
    """Connect an existing dynamic field to particle/nCloth/nParticle objects.

    Uses ``cmds.connectDynamic(fields=field_node)`` to wire the field
    forces to the given dynamic objects.

    Args:
        field_node: Name of the existing dynamic field node (or its
            transform).
        objects: List of dynamic object names (particle, nParticle,
            nCloth, nRigid) to receive the field influence.

    Returns:
        ActionResultModel dict with ``context.field_node`` and
        ``context.connected_objects``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one dynamic object name",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(field_node):
            return error_result(
                "Field node not found: {}".format(field_node),
                "'{}' does not exist in the scene".format(field_node),
            ).to_dict()

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist before connecting the field",
            ).to_dict()

        cmds.connectDynamic(objects, fields=field_node)

        return success_result(
            "Connected field '{}' to {} object(s)".format(field_node, len(objects)),
            field_node=field_node,
            connected_objects=list(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("connect_field_to_objects failed")
        return error_result("Failed to connect field '{}' to objects".format(field_node), str(exc)).to_dict()


def create_ncloth(
    mesh: str,
    nucleus: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Create an nCloth dynamic cloth node on a polygon mesh.

    The mesh is converted to nCloth by calling ``cmds.nCloth`` on it.
    The nCloth node is optionally connected to a specific nucleus solver;
    otherwise Maya uses the default nucleus in the scene (or creates one).

    Args:
        mesh: Name of the polygon mesh transform to make into nCloth.
        nucleus: Optional name of an existing nucleus solver to connect the
            nCloth node to.  If ``None``, Maya's default nucleus is used.
        name: Optional name for the nCloth shape node.

    Returns:
        ActionResultModel dict with ``context.ncloth_node``,
        ``context.mesh``, ``context.nucleus``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            ).to_dict()

        mesh_type = cmds.objectType(mesh)
        if mesh_type not in ("transform", "mesh"):
            return error_result(
                "Invalid mesh type: {}".format(mesh_type),
                "'{}' is not a polygon mesh or transform".format(mesh),
            ).to_dict()

        if nucleus and not cmds.objExists(nucleus):
            return error_result(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            ).to_dict()

        # Select the mesh and create nCloth
        cmds.select(mesh, replace=True)
        ncloth_kwargs = {}
        if name:
            ncloth_kwargs["name"] = name
        result = cmds.nCloth(**ncloth_kwargs)
        ncloth_node = result[0] if isinstance(result, (list, tuple)) else result

        # Connect to specific nucleus if requested
        if nucleus:
            cmds.connectAttr(
                "{}.startFrame".format(nucleus),
                "{}.startFrame".format(ncloth_node),
                force=True,
            )

        used_nucleus = nucleus or "default"
        return success_result(
            "Created nCloth '{}' on mesh '{}'".format(ncloth_node, mesh),
            ncloth_node=ncloth_node,
            mesh=mesh,
            nucleus=used_nucleus,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_ncloth failed")
        return error_result("Failed to create nCloth on '{}'".format(mesh), str(exc)).to_dict()


def create_nrigid(
    mesh: str,
    nucleus: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Create a passive nRigid collider node on a polygon mesh.

    The mesh is converted to a passive nRigid collider by calling
    ``cmds.nRigid`` on it.  This allows nCloth and nParticle simulations to
    collide with the mesh.

    Args:
        mesh: Name of the polygon mesh transform to use as a collider.
        nucleus: Optional name of an existing nucleus solver to connect the
            nRigid node to.  If ``None``, Maya's default nucleus is used.
        name: Optional name for the nRigid shape node.

    Returns:
        ActionResultModel dict with ``context.nrigid_node``,
        ``context.mesh``, ``context.nucleus``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            ).to_dict()

        mesh_type = cmds.objectType(mesh)
        if mesh_type not in ("transform", "mesh"):
            return error_result(
                "Invalid mesh type: {}".format(mesh_type),
                "'{}' is not a polygon mesh or transform".format(mesh),
            ).to_dict()

        if nucleus and not cmds.objExists(nucleus):
            return error_result(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            ).to_dict()

        cmds.select(mesh, replace=True)
        nrigid_kwargs = {}
        if name:
            nrigid_kwargs["name"] = name
        result = cmds.nRigid(**nrigid_kwargs)
        nrigid_node = result[0] if isinstance(result, (list, tuple)) else result

        if nucleus:
            cmds.connectAttr(
                "{}.startFrame".format(nucleus),
                "{}.startFrame".format(nrigid_node),
                force=True,
            )

        used_nucleus = nucleus or "default"
        return success_result(
            "Created nRigid '{}' on mesh '{}'".format(nrigid_node, mesh),
            nrigid_node=nrigid_node,
            mesh=mesh,
            nucleus=used_nucleus,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_nrigid failed")
        return error_result("Failed to create nRigid on '{}'".format(mesh), str(exc)).to_dict()


def set_ncloth_attribute(
    ncloth_node: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute on a Maya nCloth shape node.

    Commonly used attributes include ``"thickness"``, ``"bounce"``,
    ``"friction"``, ``"stickiness"``, ``"stretchResistance"``,
    ``"compressionResistance"``, ``"bendResistance"``, ``"damp"``,
    ``"inputMeshAttract"``, ``"lift"``, ``"drag"``.

    Args:
        ncloth_node: Name of the nCloth shape node (not the mesh transform).
        attribute: Attribute name on the nCloth node.
        value: Scalar float value, or ``[x, y, z]`` list for triple attrs.

    Returns:
        ActionResultModel dict with ``context.ncloth_node``,
        ``context.attribute``, ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ncloth_node):
            return error_result(
                "nCloth node not found: {}".format(ncloth_node),
                "'{}' does not exist in the scene".format(ncloth_node),
            ).to_dict()

        node_type = cmds.objectType(ncloth_node)
        if node_type != "nCloth":
            return error_result(
                "Not an nCloth node: {}".format(ncloth_node),
                "Expected node type 'nCloth', got '{}'".format(node_type),
            ).to_dict()

        plug = "{}.{}".format(ncloth_node, attribute)
        if not cmds.objExists(plug):
            return error_result(
                "Attribute not found: {}".format(plug),
                "'{}' does not have attribute '{}'".format(ncloth_node, attribute),
            ).to_dict()

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(plug, value, type="string")
        else:
            cmds.setAttr(plug, value)

        return success_result(
            "Set '{}.{}' = {}".format(ncloth_node, attribute, value),
            ncloth_node=ncloth_node,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_ncloth_attribute failed")
        return error_result("Failed to set attribute on nCloth '{}'".format(ncloth_node), str(exc)).to_dict()


def list_ncloth_nodes() -> dict:
    """List all nCloth shape nodes in the current Maya scene.

    Returns basic information about each nCloth node including its name,
    parent transform, and the connected nucleus solver (if any).

    Returns:
        ActionResultModel dict with ``context.nodes`` (list of dicts) and
        ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ncloth_shapes = cmds.ls(type="nCloth") or []

        nodes = []
        for shape in ncloth_shapes:
            parent_transforms = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            parent = parent_transforms[0] if parent_transforms else None

            # Try to find connected nucleus solver
            nucleus = None
            connections = cmds.listConnections("{}.startFrame".format(shape), source=True, destination=False) or []
            for conn in connections:
                if cmds.objectType(conn) == "nucleus":
                    nucleus = conn
                    break

            nodes.append(
                {
                    "name": shape,
                    "transform": parent,
                    "nucleus": nucleus,
                }
            )

        return success_result(
            "Found {} nCloth node(s) in scene".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_ncloth_nodes failed")
        return error_result("Failed to list nCloth nodes", str(exc)).to_dict()


def set_nrigid_attribute(
    nrigid_node,  # type: str
    attribute,  # type: str
    value,  # type: object
):
    # type: (...) -> dict
    """Set an attribute on a Maya nRigid (passive collider) shape node.

    Args:
        nrigid_node: Name of the nRigid shape node.
        attribute: Attribute name to set (e.g. ``"thickness"``, ``"bounce"``).
        value: New value. Scalar, triple-list (``[r, g, b]`` / ``[x, y, z]``),
            or string.

    Returns:
        ActionResultModel dict with ``context.nrigid_node``,
        ``context.attribute``, ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not nrigid_node or not attribute:
        return error_result(
            "nrigid_node and attribute are required",
            "Provide non-empty nrigid_node and attribute strings",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(nrigid_node):
            return error_result(
                "nRigid node not found: {}".format(nrigid_node),
                "'{}' does not exist in the scene".format(nrigid_node),
            ).to_dict()

        node_type = cmds.objectType(nrigid_node)
        if node_type != "nRigid":
            return error_result(
                "Not an nRigid node: {}".format(nrigid_node),
                "Expected node type 'nRigid', got '{}'".format(node_type),
            ).to_dict()

        attr_path = "{}.{}".format(nrigid_node, attribute)
        if not cmds.objExists(attr_path):
            return error_result(
                "Attribute not found: {}".format(attr_path),
                "'{}' does not have attribute '{}'".format(nrigid_node, attribute),
            ).to_dict()

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(attr_path, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(nrigid_node, attribute, value),
            nrigid_node=nrigid_node,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_nrigid_attribute failed")
        return error_result(
            "Failed to set attribute '{}' on '{}'".format(attribute, nrigid_node),
            str(exc),
        ).to_dict()


def list_nrigid_nodes():
    # type: () -> dict
    """List all nRigid (passive collider) shape nodes in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.nodes`` (list of dicts with
        ``name``, ``transform``, ``nucleus``) and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nrigid_shapes = cmds.ls(type="nRigid") or []

        nodes = []
        for shape in nrigid_shapes:
            parent_transforms = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            parent = parent_transforms[0] if parent_transforms else None

            nucleus = None
            connections = cmds.listConnections("{}.startFrame".format(shape), source=True, destination=False) or []
            for conn in connections:
                if cmds.objectType(conn) == "nucleus":
                    nucleus = conn
                    break

            nodes.append(
                {
                    "name": shape,
                    "transform": parent,
                    "nucleus": nucleus,
                }
            )

        return success_result(
            "Found {} nRigid node(s) in scene".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_nrigid_nodes failed")
        return error_result("Failed to list nRigid nodes", str(exc)).to_dict()
