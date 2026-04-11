"""Maya rigging and skeleton actions."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional


def create_joint(
    name: Optional[str] = None,
    position: Optional[List[float]] = None,
    parent: Optional[str] = None,
) -> dict:
    """Create a Maya joint node.

    Joints are the fundamental building blocks for skeletal rigs used in
    character animation.  If a *parent* is specified the joint is created as
    a child of that node; otherwise it is placed at the world root.

    Args:
        name: Optional name for the new joint.  Maya generates a default name
            (``"joint1"``, ``"joint2"``, …) when None.
        position: World-space ``[x, y, z]`` position.  Defaults to
            ``[0, 0, 0]``.
        parent: Name of an existing transform/joint to parent the new joint
            under.  If None, the joint is created at the world root.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.position``, and ``context.parent``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if parent and not cmds.objExists(parent):
            return maya_error(
                "Parent not found: {}".format(parent),
                "'{}' does not exist in the scene".format(parent),
            )

        pos = position or [0.0, 0.0, 0.0]
        if len(pos) != 3:
            return maya_error(
                "Invalid position",
                "position must be a list of 3 floats, got: {}".format(pos),
            )

        # Select parent first so joint is created as its child
        if parent:
            cmds.select(parent, replace=True)
        else:
            cmds.select(clear=True)

        kwargs = {"position": (pos[0], pos[1], pos[2])}
        if name:
            kwargs["name"] = name

        joint_name = cmds.joint(**kwargs)

        return maya_success(
            "Created joint '{}'".format(joint_name),
            object_name=joint_name,
            position=pos,
            parent=parent,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create joint")


def create_curve(
    points: Optional[List[List[float]]] = None,
    name: Optional[str] = None,
    degree: int = 3,
    periodic: bool = False,
) -> dict:
    """Create a NURBS curve from a list of control points.

    Args:
        points: List of ``[x, y, z]`` control-point positions.  A minimum of
            ``degree + 1`` points is required (e.g. 4 points for degree-3).
            Defaults to a simple line along the X axis if not provided.
        name: Optional name for the curve's transform node.
        degree: Curve degree.  Typical values: ``1`` (linear), ``3`` (cubic).
            Default: ``3``.
        periodic: If True, creates a closed (periodic) curve.  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.degree``, ``context.point_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if points is None:
            # Default: a straight line with degree+2 CV points along X
            points = [[float(i), 0.0, 0.0] for i in range(degree + 2)]

        if len(points) < degree + 1:
            return maya_error(
                "Not enough control points",
                "Need at least {} points for degree-{} curve, got {}".format(degree + 1, degree, len(points)),
            )

        point_tuples = [(p[0], p[1], p[2]) for p in points]
        periodic_val = 2 if periodic else 0  # 0=open, 2=periodic

        kwargs = {
            "point": point_tuples,
            "degree": degree,
            "periodic": periodic_val,
        }
        if name:
            kwargs["name"] = name

        result = cmds.curve(**kwargs)

        return maya_success(
            "Created NURBS curve '{}'".format(result),
            object_name=result,
            degree=degree,
            point_count=len(points),
            periodic=periodic,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create curve")


def set_joint_orient(
    joint_name: str,
    orient: Optional[List[float]] = None,
    zero_scale_orient: bool = False,
) -> dict:
    """Set the joint orientation of a Maya joint node.

    Joint orientation defines the local rotation axes used by the joint and
    affects how rotation channels are interpreted downstream in the rig.

    Args:
        joint_name: Name of the joint to orient.
        orient: ``[x, y, z]`` orientation in degrees.  Defaults to
            ``[0, 0, 0]`` (zero out joint orient).
        zero_scale_orient: If True, also zeroes the scale-compensate orient
            (``jointOrientX/Y/Z``).  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name`` and
        ``context.orient``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(joint_name):
            return maya_error(
                "Joint not found: {}".format(joint_name),
                "'{}' does not exist in the scene".format(joint_name),
            )

        node_type = cmds.objectType(joint_name)
        if node_type != "joint":
            return maya_error(
                "Not a joint: {}".format(joint_name),
                "'{}' is of type '{}', expected 'joint'".format(joint_name, node_type),
            )

        ox, oy, oz = (orient or [0.0, 0.0, 0.0])[:3]
        cmds.setAttr("{}.jointOrientX".format(joint_name), ox)
        cmds.setAttr("{}.jointOrientY".format(joint_name), oy)
        cmds.setAttr("{}.jointOrientZ".format(joint_name), oz)

        if zero_scale_orient:
            for ax in ("X", "Y", "Z"):
                cmds.setAttr("{}.segmentScaleCompensate".format(joint_name), True)

        return maya_success(
            "Set joint orient on '{}' to [{}, {}, {}]".format(joint_name, ox, oy, oz),
            object_name=joint_name,
            orient=[ox, oy, oz],
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set joint orient on {}".format(joint_name))


def mirror_joints(
    joint_name: str,
    mirror_behavior: bool = True,
    search_replace: Optional[List[str]] = None,
    mirror_axis: str = "YZ",
) -> dict:
    """Mirror a joint chain across an axis plane.

    Creates a mirrored copy of the joint chain starting at *joint_name*.  The
    most common use case is to build a symmetric rig (left-to-right or vice
    versa) with a single call.

    Args:
        joint_name: Root joint of the chain to mirror.
        mirror_behavior: If True, uses Maya's ``mirrorBehavior`` flag to
            invert the orientation of mirrored joints.  Default: True.
        search_replace: Two-element list ``[search, replace]`` used to rename
            mirrored joints (e.g. ``["L_", "R_"]``).  Defaults to
            ``["L_", "R_"]``.
        mirror_axis: Plane to mirror across – one of ``"YZ"``, ``"XY"``,
            ``"XZ"``.  Default: ``"YZ"``.

    Returns:
        ActionResultModel dict with ``context.mirrored_joints`` list.
    """

    _VALID_AXES = ("YZ", "XY", "XZ")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(joint_name):
            return maya_error(
                "Joint not found: {}".format(joint_name),
                "'{}' does not exist in the scene".format(joint_name),
            )

        if mirror_axis not in _VALID_AXES:
            return maya_error(
                "Invalid mirror axis: {}".format(mirror_axis),
                "mirror_axis must be one of {}".format(_VALID_AXES),
            )

        sr = search_replace or ["L_", "R_"]
        if len(sr) != 2:
            return maya_error(
                "Invalid search_replace",
                "search_replace must be a list of exactly two strings",
            )

        axis_kwargs = {
            "YZ": {"mirrorYZ": True},
            "XY": {"mirrorXY": True},
            "XZ": {"mirrorXZ": True},
        }[mirror_axis]

        mirrored = cmds.mirrorJoint(joint_name, mirrorBehavior=mirror_behavior, searchReplace=sr, **axis_kwargs)

        return maya_success(
            "Mirrored joint chain from '{}'".format(joint_name),
            source_joint=joint_name,
            mirrored_joints=list(mirrored) if mirrored else [],
            mirror_axis=mirror_axis,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to mirror joints from {}".format(joint_name))


def create_ik_handle(
    start_joint: str,
    end_joint: str,
    solver: str = "ikRPsolver",
    name: Optional[str] = None,
) -> dict:
    """Create an IK handle between two joints.

    Args:
        start_joint: Name of the start (root) joint of the IK chain.
        end_joint: Name of the end (tip) joint of the IK chain.
        solver: IK solver to use.  Supported values:
            ``"ikRPsolver"`` (Rotate-Plane, default) or
            ``"ikSCsolver"`` (Single-Chain).
        name: Optional name for the IK handle node.  Maya auto-generates a
            name when None.

    Returns:
        ActionResultModel dict with ``context.handle_name``,
        ``context.effector_name``, and ``context.solver``.
    """

    _VALID_SOLVERS = ("ikRPsolver", "ikSCsolver")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(start_joint):
            return maya_error(
                "Start joint not found: {}".format(start_joint),
                "'{}' does not exist in the scene".format(start_joint),
            )

        if not cmds.objExists(end_joint):
            return maya_error(
                "End joint not found: {}".format(end_joint),
                "'{}' does not exist in the scene".format(end_joint),
            )

        if solver not in _VALID_SOLVERS:
            return maya_error(
                "Invalid solver: {}".format(solver),
                "solver must be one of {}".format(_VALID_SOLVERS),
            )

        kwargs = {
            "startJoint": start_joint,
            "endEffector": end_joint,
            "solver": solver,
        }
        if name:
            kwargs["name"] = name

        result = cmds.ikHandle(**kwargs)
        handle_name = result[0]
        effector_name = result[1]

        return maya_success(
            "Created IK handle '{}'".format(handle_name),
            handle_name=handle_name,
            effector_name=effector_name,
            start_joint=start_joint,
            end_joint=end_joint,
            solver=solver,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create IK handle")


def assign_deformer(
    object_name: str,
    deformer_type: str = "cluster",
) -> dict:
    """Apply a deformer to an object.

    Supported deformer types: ``"cluster"``, ``"blendShape"``, ``"lattice"``,
    ``"wrap"``, ``"nonLinear"`` (bend/twist/flare/sine/squash/wave).

    Args:
        object_name: Name of the mesh/surface to deform.
        deformer_type: Deformer type string.  Default: ``"cluster"``.

    Returns:
        ActionResultModel dict with ``context.deformer_name``,
        ``context.handle_name`` (for cluster/lattice) if applicable.
    """

    _SUPPORTED = ("cluster", "blendShape", "lattice", "wrap", "bend", "twist", "flare", "sine", "squash", "wave")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if deformer_type not in _SUPPORTED:
            return maya_error(
                "Unsupported deformer type: {}".format(deformer_type),
                "deformer_type must be one of {}".format(_SUPPORTED),
            )

        cmds.select(object_name, replace=True)

        if deformer_type == "cluster":
            result = cmds.cluster(object_name)
            deformer_name = result[0]
            handle_name = result[1] if len(result) > 1 else None
            return maya_success(
                "Applied cluster deformer to '{}'".format(object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                handle_name=handle_name,
                deformer_type=deformer_type,
                prompt="Check the result with list_scripting or use related actions to continue.",
            )

        if deformer_type == "lattice":
            result = cmds.lattice(object_name)
            deformer_name = result[0]
            return maya_success(
                "Applied lattice deformer to '{}'".format(object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                deformer_type=deformer_type,
                prompt="Check the result with list_scripting or use related actions to continue.",
            )

        if deformer_type in ("bend", "twist", "flare", "sine", "squash", "wave"):
            result = cmds.nonLinear(object_name, type=deformer_type)
            deformer_name = result[0]
            handle_name = result[1] if len(result) > 1 else None
            return maya_success(
                "Applied {} deformer to '{}'".format(deformer_type, object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                handle_name=handle_name,
                deformer_type=deformer_type,
                prompt="Check the result with list_scripting or use related actions to continue.",
            )

        # blendShape / wrap — generic path
        result = cmds.deformer(object_name, type=deformer_type)
        deformer_name = result[0] if result else deformer_type
        return maya_success(
            "Applied {} deformer to '{}'".format(deformer_type, object_name),
            object_name=object_name,
            deformer_name=deformer_name,
            deformer_type=deformer_type,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to assign deformer to {}".format(object_name))


def create_blend_shape(
    base_mesh: str,
    target_meshes: Optional[List[str]] = None,
    name: Optional[str] = None,
    origin: str = "local",
) -> dict:
    """Create a blend shape deformer on a base mesh with optional targets.

    Args:
        base_mesh: Name of the base (destination) mesh.
        target_meshes: List of target mesh names whose shapes drive the blend.
            If None or empty, a zero-target blend shape node is created.
        name: Optional name for the blend shape node.
        origin: ``"local"`` (default) or ``"world"`` space blend.

    Returns:
        ActionResultModel dict with ``context.blend_shape_name``,
        ``context.target_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(base_mesh):
            return maya_error(
                "Base mesh not found: {}".format(base_mesh),
                "'{}' does not exist in the scene".format(base_mesh),
            )

        targets = target_meshes or []
        missing = [t for t in targets if not cmds.objExists(t)]
        if missing:
            return maya_error(
                "Target meshes not found: {}".format(", ".join(missing)),
                "The following targets do not exist: {}".format(", ".join(missing)),
            )

        all_meshes = targets + [base_mesh]
        kwargs = {"origin": origin}  # type: dict
        if name:
            kwargs["name"] = name

        result = cmds.blendShape(*all_meshes, **kwargs)
        bs_name = result[0] if result else (name or "blendShape1")

        return maya_success(
            "Created blend shape '{}' on '{}'".format(bs_name, base_mesh),
            blend_shape_name=bs_name,
            base_mesh=base_mesh,
            target_count=len(targets),
            targets=targets,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create blend shape on {}".format(base_mesh))


def skin_cluster_bind(
    joints: List[str],
    mesh: str,
    max_influences: int = 4,
    bind_method: int = 0,
    name: Optional[str] = None,
) -> dict:
    """Bind a mesh to a set of joints using a skin cluster.

    Args:
        joints: List of joint names to include in the skin cluster.
        mesh: Name of the mesh to skin.
        max_influences: Maximum number of joints that can influence each
            vertex.  Default: 4.
        bind_method: Binding algorithm:
            ``0`` = closest distance (default),
            ``1`` = closest joint,
            ``2`` = heat map,
            ``3`` = geodesic voxel.
        name: Optional name for the skin cluster node.

    Returns:
        ActionResultModel dict with ``context.skin_cluster_name``,
        ``context.joint_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not joints:
            return maya_error(
                "No joints specified",
                "joints list must contain at least one joint name",
            )

        if not cmds.objExists(mesh):
            return maya_error(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            )

        missing = [j for j in joints if not cmds.objExists(j)]
        if missing:
            return maya_error(
                "Joints not found: {}".format(", ".join(missing)),
                "The following joints do not exist: {}".format(", ".join(missing)),
            )

        objects = list(joints) + [mesh]
        kwargs = {
            "maximumInfluences": max_influences,
            "bindMethod": bind_method,
            "toSelectedBones": True,
        }  # type: dict
        if name:
            kwargs["name"] = name

        result = cmds.skinCluster(*objects, **kwargs)
        sc_name = result[0] if result else (name or "skinCluster1")

        return maya_success(
            "Bound '{}' to {} joint(s) via skin cluster '{}'".format(mesh, len(joints), sc_name),
            skin_cluster_name=sc_name,
            mesh=mesh,
            joint_count=len(joints),
            joints=joints,
            max_influences=max_influences,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to bind skin cluster on {}".format(mesh))


def set_joint_limit(
    joint_name: str,
    axis: str,
    min_angle: Optional[float] = None,
    max_angle: Optional[float] = None,
    enable: bool = True,
) -> dict:
    """Set rotation limits on a joint axis.

    Limits constrain how far a joint can rotate on a given axis, preventing
    unrealistic poses during animation or IK solving.

    Args:
        joint_name: Name of the joint node to configure.
        axis: Rotation axis to limit – one of ``"x"``, ``"y"``, ``"z"``.
        min_angle: Minimum rotation angle in degrees.  If None, the existing
            minimum limit is left unchanged.
        max_angle: Maximum rotation angle in degrees.  If None, the existing
            maximum limit is left unchanged.
        enable: If True (default), enable the limit on the specified axis.
            Set to False to disable the limit without changing the stored angle
            values.

    Returns:
        ActionResultModel dict with ``context.joint_name``,
        ``context.axis``, ``context.min_angle``, ``context.max_angle``,
        ``context.enable``.
    """

    _VALID_AXES = ("x", "y", "z")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(joint_name):
            return maya_error(
                "Joint not found: {}".format(joint_name),
                "'{}' does not exist in the scene".format(joint_name),
            )

        node_type = cmds.objectType(joint_name)
        if node_type != "joint":
            return maya_error(
                "Not a joint: {}".format(joint_name),
                "'{}' is of type '{}', expected 'joint'".format(joint_name, node_type),
            )

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return maya_error(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            )

        axis_upper = axis_lower.upper()
        enable_attr_min = "minRot{}LimitEnable".format(axis_upper)
        enable_attr_max = "maxRot{}LimitEnable".format(axis_upper)
        min_attr = "minRot{}Limit".format(axis_upper)
        max_attr = "maxRot{}Limit".format(axis_upper)

        cmds.setAttr("{}.{}".format(joint_name, enable_attr_min), enable)
        cmds.setAttr("{}.{}".format(joint_name, enable_attr_max), enable)

        if min_angle is not None:
            cmds.setAttr("{}.{}".format(joint_name, min_attr), min_angle)
        if max_angle is not None:
            cmds.setAttr("{}.{}".format(joint_name, max_attr), max_angle)

        # Read back the actual stored values
        actual_min = cmds.getAttr("{}.{}".format(joint_name, min_attr))
        actual_max = cmds.getAttr("{}.{}".format(joint_name, max_attr))

        return maya_success(
            "Set rotation limit on '{}.{}': [{}, {}]".format(joint_name, axis_lower, actual_min, actual_max),
            joint_name=joint_name,
            axis=axis_lower,
            min_angle=actual_min,
            max_angle=actual_max,
            enable=enable,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set joint limit on {}".format(joint_name))


def blend_shape_add_target(
    blend_shape: str,
    target_mesh: str,
    weight: float = 0.0,
    index: Optional[int] = None,
) -> dict:
    """Add a target mesh to an existing blend shape deformer.

    Args:
        blend_shape: Name of the blendShape node to modify.
        target_mesh: Name of the mesh to use as the new blend shape target.
        weight: Initial weight value for the new target (0.0–1.0).
            Default: 0.0.
        index: Target index slot.  If None, Maya assigns the next available
            index automatically.

    Returns:
        ActionResultModel dict with ``context.blend_shape``,
        ``context.target_mesh``, ``context.target_index``.
    """

    if not (0.0 <= weight <= 1.0):
        return maya_error(
            "Invalid weight: {}".format(weight),
            "weight must be between 0.0 and 1.0",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(blend_shape):
            return maya_error("Blend shape not found: {}".format(blend_shape))

        node_type = cmds.objectType(blend_shape)
        if node_type != "blendShape":
            return maya_error("'{}' is not a blendShape node (type: {})".format(blend_shape, node_type))

        if not cmds.objExists(target_mesh):
            return maya_error("Target mesh not found: {}".format(target_mesh))

        # Determine target index
        if index is None:
            existing = cmds.blendShape(blend_shape, query=True, weightCount=True) or 0
            target_index = int(existing)
        else:
            target_index = int(index)

        cmds.blendShape(
            blend_shape,
            edit=True,
            target=(
                cmds.blendShape(blend_shape, query=True, geometry=True)[0],
                target_index,
                target_mesh,
                weight,
            ),
        )

        return maya_success(
            "Added target '{}' to blend shape '{}' at index {}".format(target_mesh, blend_shape, target_index),
            blend_shape=blend_shape,
            target_mesh=target_mesh,
            target_index=target_index,
            weight=weight,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add blend shape target")


def set_driven_key(
    driver_attr: str,
    driven_attrs: List[str],
    driver_values: List[float],
    driven_values: List[List[float]],
    tangent_type: str = "linear",
) -> dict:
    """Create a set-driven key relationship between a driver and driven attrs.

    A set-driven key creates an animation curve so that when *driver_attr*
    reaches each value in *driver_values*, each driven attribute in
    *driven_attrs* takes the corresponding value in *driven_values*.

    Args:
        driver_attr: Full attribute path for the driver (e.g.
            ``"ctrl.rotateY"``).
        driven_attrs: List of full attribute paths for driven attrs (e.g.
            ``["joint1.translateX", "joint1.translateZ"]``).
        driver_values: List of driver values that define the key positions.
            Must have at least 1 entry.
        driven_values: 2-D list ``[per_driver_value][per_driven_attr]``.
            ``driven_values[i][j]`` is the value of ``driven_attrs[j]`` when
            ``driver_attr == driver_values[i]``.
        tangent_type: Tangent type for the keys — ``"linear"``, ``"smooth"``,
            ``"flat"``, or ``"step"``.  Default: ``"linear"``.

    Returns:
        ActionResultModel dict with ``context.driver_attr``,
        ``context.driven_attrs``, ``context.key_count``.
    """

    _VALID_TANGENTS = ("linear", "smooth", "flat", "step")

    if not driver_values:
        return maya_error(
            "driver_values cannot be empty",
            "Provide at least one driver value",
        )

    if len(driven_values) != len(driver_values):
        return maya_error(
            "Mismatched driver/driven value counts",
            "driven_values must have the same length as driver_values",
        )

    if tangent_type not in _VALID_TANGENTS:
        return maya_error(
            "Invalid tangent_type: {}".format(tangent_type),
            "Use one of: {}".format(", ".join(_VALID_TANGENTS)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        driver_obj = driver_attr.rsplit(".", 1)[0]
        if not cmds.objExists(driver_obj):
            return maya_error("Driver object not found: {}".format(driver_obj))

        for da in driven_attrs:
            da_obj = da.rsplit(".", 1)[0]
            if not cmds.objExists(da_obj):
                return maya_error("Driven object not found: {}".format(da_obj))

        keys_set = 0
        for i, drv_val in enumerate(driver_values):
            cmds.setAttr(driver_attr, drv_val)
            row = driven_values[i]
            for j, da in enumerate(driven_attrs):
                da_val = row[j] if j < len(row) else 0.0
                cmds.setAttr(da, da_val)
                cmds.setDrivenKeyframe(
                    da,
                    currentDriver=driver_attr,
                    inTangentType=tangent_type,
                    outTangentType=tangent_type,
                )
                keys_set += 1

        return maya_success(
            "Set driven key: '{}' drives {} attr(s) with {} key(s)".format(
                driver_attr, len(driven_attrs), len(driver_values)
            ),
            driver_attr=driver_attr,
            driven_attrs=driven_attrs,
            key_count=len(driver_values),
            keys_set=keys_set,
            tangent_type=tangent_type,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set driven key")


def set_ik_fk_blend(
    ik_handle: str,
    blend: float = 1.0,
    attribute: str = "ikBlend",
) -> dict:
    """Set the IK/FK blend weight on an IK handle.

    Most IK solvers expose an ``ikBlend`` attribute (0 = full FK,
    1 = full IK).  This action sets that blend value and optionally
    creates a keyframe on it.

    Args:
        ik_handle: Name of the IK handle node.
        blend: Blend value between 0.0 (FK) and 1.0 (IK).  Default: 1.0.
        attribute: Name of the blend attribute on the IK handle.
            Default: ``"ikBlend"``.

    Returns:
        ActionResultModel dict with ``context.ik_handle``,
        ``context.attribute``, ``context.blend``.
    """

    if not (0.0 <= blend <= 1.0):
        return maya_error(
            "blend must be in the range [0.0, 1.0]",
            "Got blend={}".format(blend),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ik_handle):
            return maya_error(
                "IK handle not found: {}".format(ik_handle),
                "'{}' does not exist in the scene".format(ik_handle),
            )

        node_type = cmds.objectType(ik_handle)
        if node_type not in ("ikHandle", "transform"):
            return maya_error(
                "Not an IK handle: {}".format(ik_handle),
                "'{}' is of type '{}'; expected 'ikHandle'".format(ik_handle, node_type),
            )

        plug = "{}.{}".format(ik_handle, attribute)
        if not cmds.objExists(plug):
            return maya_error(
                "Attribute not found: {}".format(plug),
                "IK handle '{}' does not have attribute '{}'".format(ik_handle, attribute),
            )

        cmds.setAttr(plug, blend)

        return maya_success(
            "Set IK/FK blend on '{}' to {}".format(ik_handle, blend),
            ik_handle=ik_handle,
            attribute=attribute,
            blend=blend,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set IK/FK blend on '{}'".format(ik_handle))
