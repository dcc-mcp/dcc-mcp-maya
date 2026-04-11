"""Create a weighted multi-source constraint."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_CONSTRAINT_TYPES = {
    "parent": "parentConstraint",
    "point": "pointConstraint",
    "orient": "orientConstraint",
    "scale": "scaleConstraint",
    "aim": "aimConstraint",
}


def create_constraint_weighted(
    constraint_type: str,
    sources: List[str],
    target: str,
    weights: Optional[List[float]] = None,
    maintain_offset: bool = True,
) -> dict:
    """Create a weighted multi-source constraint.

    Args:
        constraint_type: One of ``parent``, ``point``, ``orient``, ``scale``, ``aim``.
        sources: List of driver (source) object names.  At least two required
            for a weighted constraint.
        target: Name of the driven (target) object.
        weights: Optional weight per source.  Defaults to 1.0 for each source.
        maintain_offset: Preserve current offsets.

    Returns:
        ActionResultModel dict with ``context.constraint_node`` and
        ``context.source_weights``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if constraint_type not in _CONSTRAINT_TYPES:
            return error_result(
                "Unknown constraint type: {}".format(constraint_type),
                "Supported types: {}".format(", ".join(sorted(_CONSTRAINT_TYPES))),
            ).to_dict()

        if len(sources) < 1:
            return error_result("No sources provided", "At least one source object is required").to_dict()

        for obj in sources + [target]:
            if not cmds.objExists(obj):
                return error_result(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist".format(obj),
                ).to_dict()

        effective_weights = weights if weights and len(weights) == len(sources) else [1.0] * len(sources)

        cmd_fn = getattr(cmds, _CONSTRAINT_TYPES[constraint_type])

        # Create constraint with first source
        result = cmd_fn(sources[0], target, maintainOffset=maintain_offset, weight=effective_weights[0])
        constraint_node = result[0] if result else ""

        # Add remaining sources with their weights
        for i, src in enumerate(sources[1:], 1):
            cmd_fn(src, target, edit=True, weight=effective_weights[i])
            # Add the source — re-call with add=True to include it
            cmd_fn(src, target, maintainOffset=maintain_offset, weight=effective_weights[i])

        source_weights = list(zip(sources, effective_weights))

        return success_result(
            "Created weighted {} constraint on '{}' with {} sources".format(constraint_type, target, len(sources)),
            prompt="Use list_constraints to inspect the result or remove_constraint to undo.",
            constraint_node=constraint_node,
            constraint_type=constraint_type,
            target=target,
            source_weights=[{"source": s, "weight": w} for s, w in source_weights],
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_constraint_weighted failed")
        return error_result("Failed to create weighted constraint", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_constraint_weighted`."""
    return create_constraint_weighted(**kwargs)


if __name__ == "__main__":
    import json

    result = create_constraint_weighted("parent", ["pSphere1", "pCube1"], "pCylinder1", [0.7, 0.3])
    print(json.dumps(result))
