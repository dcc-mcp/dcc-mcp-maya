"""Edit common Maya rigid body properties."""

from __future__ import annotations

from typing import Any, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _normalise_mode(mode: Optional[str]) -> Optional[str]:
    if mode is None:
        return None
    lowered = str(mode).strip().lower()
    if lowered not in {"active", "passive"}:
        raise ValueError("mode must be 'active' or 'passive'")
    return lowered


def set_rigid_body_properties(
    rigid_bodies: List[str],
    mode: Optional[str] = None,
    mass: Optional[float] = None,
    bounciness: Optional[float] = None,
    damping: Optional[float] = None,
    static_friction: Optional[float] = None,
    dynamic_friction: Optional[float] = None,
    collisions: Optional[bool] = None,
) -> dict:
    """Edit common properties on one or more existing rigid body nodes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = _as_list(rigid_bodies)
        if not targets:
            return maya_error("No rigid bodies provided", "Pass one or more rigid body node names.")
        err = batch_validate_nodes(cmds, targets)
        if err:
            return err

        updates = {}
        resolved_mode = _normalise_mode(mode)
        if resolved_mode == "active":
            updates["active"] = True
        elif resolved_mode == "passive":
            updates["passive"] = True
        if mass is not None:
            updates["mass"] = float(mass)
        if bounciness is not None:
            updates["bounciness"] = float(bounciness)
        if damping is not None:
            updates["damping"] = float(damping)
        if static_friction is not None:
            updates["staticFriction"] = float(static_friction)
        if dynamic_friction is not None:
            updates["dynamicFriction"] = float(dynamic_friction)
        if collisions is not None:
            updates["collisions"] = bool(collisions)

        if not updates:
            return maya_error(
                "No rigid body properties to update",
                "Pass at least one property such as mass, bounciness, damping, or mode.",
            )

        for body in targets:
            cmds.rigidBody(body, edit=True, **updates)

        return maya_success(
            "Updated {} rigid body node(s)".format(len(targets)),
            rigid_bodies=targets,
            updates={key: value for key, value in updates.items()},
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to update rigid body properties")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_rigid_body_properties`."""
    return set_rigid_body_properties(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
