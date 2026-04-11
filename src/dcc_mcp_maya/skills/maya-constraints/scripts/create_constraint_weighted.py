"""Create a weighted multi-source constraint."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if constraint_type not in _CONSTRAINT_TYPES:
            return skill_error(
                "Unknown constraint type: {}".format(constraint_type),
                "Supported types: {}".format(", ".join(sorted(_CONSTRAINT_TYPES))),
            )

        if len(sources) < 1:
            return skill_error("No sources provided", "At least one source object is required")

        err = batch_validate_nodes(cmds, sources + [target])
        if err:
            return err

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

        return skill_success(
            "Created weighted {} constraint on '{}' with {} sources".format(constraint_type, target, len(sources)),
            prompt="Use list_constraints to inspect the result or remove_constraint to undo.",
            constraint_node=constraint_node,
            constraint_type=constraint_type,
            target=target,
            source_weights=[{"source": s, "weight": w} for s, w in source_weights],
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create weighted constraint")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_constraint_weighted`."""
    return create_constraint_weighted(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
