"""Create a weighted multi-source constraint."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_TYPES = ("parent", "point", "orient", "scale", "aim")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not sources:
            return error_result("No sources provided", "Provide at least one source object").to_dict()

        if constraint_type not in _VALID_TYPES:
            return error_result(
                "Invalid constraint type: {}".format(constraint_type),
                "constraint_type must be one of {}".format(_VALID_TYPES),
            ).to_dict()

        if not cmds.objExists(target):
            return error_result(
                "Target not found: {}".format(target),
                "'{}' does not exist".format(target),
            ).to_dict()

        for src in sources:
            if not cmds.objExists(src):
                return error_result(
                    "Source not found: {}".format(src),
                    "'{}' does not exist".format(src),
                ).to_dict()

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

        return success_result(
            "Created weighted {} constraint on '{}' from {} sources".format(constraint_type, target, len(sources)),
            constraint_name=constraint_name,
            constraint_type=constraint_type,
            sources=sources,
            target=target,
            weights_applied=w_list[: len(sources)],
            maintain_offset=maintain_offset,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_constraint_weighted failed")
        return error_result("Failed to create weighted {} constraint".format(constraint_type), str(exc)).to_dict()



def main(**kwargs):
    return create_constraint_weighted(**kwargs)


if __name__ == "__main__":
    import json
    result = create_constraint_weighted()
    print(json.dumps(result))
