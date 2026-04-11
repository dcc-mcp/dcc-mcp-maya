"""Maya constraint and node-relationship actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def add_constraint(
    source: str,
    target: str,
    constraint_type: str = "parent",
    maintain_offset: bool = True,
    name: Optional[str] = None,
) -> dict:
    """Add a Maya constraint from *source* to *target*.

    Supported constraint types: ``"parent"``, ``"point"``, ``"orient"``,
    ``"scale"``, ``"aim"``.

    Args:
        source: Name of the driver object (constrains *target* to follow this).
        target: Name of the object to be constrained.
        constraint_type: One of ``"parent"``, ``"point"``, ``"orient"``,
            ``"scale"``, ``"aim"``.  Default: ``"parent"``.
        maintain_offset: If True, preserve the current offset between the
            objects.  Default: True.
        name: Optional name for the constraint node.

    Returns:
        ActionResultModel dict with ``context.constraint_name``,
        ``context.constraint_type``, ``context.source``, ``context.target``.
    """

    _VALID_TYPES = ("parent", "point", "orient", "scale", "aim")

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

        if constraint_type not in _VALID_TYPES:
            return maya_error(
                "Invalid constraint type: {}".format(constraint_type),
                "constraint_type must be one of {}".format(_VALID_TYPES),
            )

        kwargs = {"maintainOffset": maintain_offset}
        if name:
            kwargs["name"] = name

        _CONSTRAINT_CMDS = {
            "parent": cmds.parentConstraint,
            "point": cmds.pointConstraint,
            "orient": cmds.orientConstraint,
            "scale": cmds.scaleConstraint,
            "aim": cmds.aimConstraint,
        }
        fn = _CONSTRAINT_CMDS[constraint_type]
        result = fn(source, target, **kwargs)
        constraint_name = result[0] if result else (name or "{}_{}1".format(target, constraint_type))

        return maya_success(
            "Added {} constraint: '{}' -> '{}'".format(constraint_type, source, target),
            constraint_name=constraint_name,
            constraint_type=constraint_type,
            source=source,
            target=target,
            maintain_offset=maintain_offset,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add {} constraint".format(constraint_type))


def remove_constraint(
    target: str,
    constraint_type: Optional[str] = None,
) -> dict:
    """Remove constraint(s) from a target object.

    Args:
        target: Name of the constrained object.
        constraint_type: If specified, only removes constraints of this type
            (``"parent"``, ``"point"``, ``"orient"``, ``"scale"``, ``"aim"``).
            If None, removes all supported constraints.

    Returns:
        ActionResultModel dict with ``context.removed`` list of removed
        constraint node names.
    """

    _TYPE_MAP = {
        "parent": "parentConstraint",
        "point": "pointConstraint",
        "orient": "orientConstraint",
        "scale": "scaleConstraint",
        "aim": "aimConstraint",
    }

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(target):
            return maya_error(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            )

        if constraint_type is not None and constraint_type not in _TYPE_MAP:
            return maya_error(
                "Invalid constraint type: {}".format(constraint_type),
                "constraint_type must be one of {}".format(list(_TYPE_MAP.keys())),
            )

        node_types = [_TYPE_MAP[constraint_type]] if constraint_type else list(_TYPE_MAP.values())

        removed = []
        for nt in node_types:
            constraints = cmds.listRelatives(target, type=nt) or []
            for c in constraints:
                cmds.delete(c)
                removed.append(c)

        return maya_success(
            "Removed {} constraint(s) from '{}'".format(len(removed), target),
            target=target,
            removed=removed,
            count=len(removed),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to remove constraints from {}".format(target))


def list_constraints(
    target: str,
) -> dict:
    """List all constraints applied to a target object.

    Args:
        target: Name of the constrained node to query.

    Returns:
        ActionResultModel dict with ``context.constraints`` — a list of dicts
        with ``name`` and ``type`` for each constraint found.
    """

    _CONSTRAINT_TYPES = (
        "parentConstraint",
        "pointConstraint",
        "orientConstraint",
        "scaleConstraint",
        "aimConstraint",
    )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(target):
            return maya_error(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            )

        constraints = []
        for ct in _CONSTRAINT_TYPES:
            nodes = cmds.listRelatives(target, type=ct) or []
            for node in nodes:
                constraints.append({"name": node, "type": ct})

        return maya_success(
            "Found {} constraint(s) on '{}'".format(len(constraints), target),
            target=target,
            constraints=constraints,
            count=len(constraints),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list constraints on {}".format(target))


def create_constraint_weighted(
    sources: List[str],
    target: str,
    weights: Optional[List[float]] = None,
    constraint_type: str = "parent",
    maintain_offset: bool = True,
    name: Optional[str] = None,
) -> dict:
    """Create a weighted multi-source constraint.

    Applies a single constraint node driven by multiple source objects, each
    with an individual weight value.  Supported types are the same as
    ``add_constraint``: ``"parent"``, ``"point"``, ``"orient"``,
    ``"scale"``, ``"aim"``.

    Args:
        sources: List of driver object names (at least one required).
        target: Name of the object to be constrained.
        weights: Per-source weight values (0.0 – 1.0).  If None or shorter
            than ``sources``, missing weights default to 1.0.
        constraint_type: One of ``"parent"``, ``"point"``, ``"orient"``,
            ``"scale"``, ``"aim"``.  Default: ``"parent"``.
        maintain_offset: Preserve the current offset.  Default: True.
        name: Optional name for the constraint node.

    Returns:
        ActionResultModel dict with ``context.constraint_name``,
        ``context.sources``, ``context.weights_applied``.
    """

    _VALID_TYPES = ("parent", "point", "orient", "scale", "aim")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not sources:
            return maya_error("No sources provided", "Provide at least one source object")

        if constraint_type not in _VALID_TYPES:
            return maya_error(
                "Invalid constraint type: {}".format(constraint_type),
                "constraint_type must be one of {}".format(_VALID_TYPES),
            )

        if not cmds.objExists(target):
            return maya_error(
                "Target not found: {}".format(target),
                "'{}' does not exist".format(target),
            )

        for src in sources:
            if not cmds.objExists(src):
                return maya_error(
                    "Source not found: {}".format(src),
                    "'{}' does not exist".format(src),
                )

        # Normalise weights list
        w_list = list(weights) if weights else []
        while len(w_list) < len(sources):
            w_list.append(1.0)

        _CONSTRAINT_CMDS = {
            "parent": cmds.parentConstraint,
            "point": cmds.pointConstraint,
            "orient": cmds.orientConstraint,
            "scale": cmds.scaleConstraint,
            "aim": cmds.aimConstraint,
        }
        fn = _CONSTRAINT_CMDS[constraint_type]

        kwargs = {"maintainOffset": maintain_offset, "weight": w_list[0]}
        if name:
            kwargs["name"] = name

        # Create constraint with first source and initial weight
        result = fn(sources[0], target, **kwargs)
        constraint_name = result[0] if result else (name or "{}_{}1".format(target, constraint_type))

        # Add remaining sources with their weights
        for src, w in zip(sources[1:], w_list[1:]):
            fn(src, target, edit=True, weight=w)

        # Set individual weights via constraint weight attributes
        for i, w in enumerate(w_list):
            w_attr = "{}W{}".format(sources[i], i)
            full_attr = "{}.{}".format(constraint_name, w_attr)
            if cmds.objExists(full_attr):
                cmds.setAttr(full_attr, w)

        return maya_success(
            "Created weighted {} constraint on '{}' from {} sources".format(constraint_type, target, len(sources)),
            constraint_name=constraint_name,
            constraint_type=constraint_type,
            sources=sources,
            target=target,
            weights_applied=w_list[: len(sources)],
            maintain_offset=maintain_offset,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create weighted {} constraint".format(constraint_type))
