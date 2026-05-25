"""Create Maya rigid body nodes for scene objects."""

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


def _rigid_body_name(name_prefix: Optional[str], index: int, total: int) -> Optional[str]:
    if not name_prefix:
        return None
    if total == 1:
        return str(name_prefix)
    return "{}_{:02d}".format(name_prefix, index + 1)


def _normalise_mode(mode: str) -> str:
    lowered = str(mode or "active").strip().lower()
    if lowered not in {"active", "passive"}:
        raise ValueError("mode must be 'active' or 'passive'")
    return lowered


def make_rigid_body(
    objects: Optional[List[str]] = None,
    mode: str = "active",
    name_prefix: Optional[str] = None,
    mass: float = 1.0,
    bounciness: float = 0.6,
    damping: float = 0.0,
    static_friction: float = 0.2,
    dynamic_friction: float = 0.2,
    collisions: bool = True,
) -> dict:
    """Add active or passive rigid bodies to scene objects."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = _as_list(objects) or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No objects selected for rigid bodies",
                "Provide objects or select one or more polygon/nurbs objects.",
                possible_solutions=["Pass objects=['pCube1'] or select objects before calling make_rigid_body."],
            )
        err = batch_validate_nodes(cmds, targets)
        if err:
            return err

        resolved_mode = _normalise_mode(mode)
        base_kwargs = {
            "mass": float(mass),
            "bounciness": float(bounciness),
            "damping": float(damping),
            "staticFriction": float(static_friction),
            "dynamicFriction": float(dynamic_friction),
            "collisions": bool(collisions),
        }
        if resolved_mode == "active":
            base_kwargs["active"] = True
        else:
            base_kwargs["passive"] = True

        created = []
        total = len(targets)
        for index, target in enumerate(targets):
            kwargs = dict(base_kwargs)
            rb_name = _rigid_body_name(name_prefix, index, total)
            if rb_name:
                kwargs["name"] = rb_name
            result = cmds.rigidBody(target, **kwargs)
            created.append(str(result[0] if isinstance(result, (list, tuple)) else result))

        return maya_success(
            "Created {} {} rigid body node(s)".format(len(created), resolved_mode),
            rigid_bodies=created,
            objects=targets,
            mode=resolved_mode,
            settings={
                "mass": float(mass),
                "bounciness": float(bounciness),
                "damping": float(damping),
                "static_friction": float(static_friction),
                "dynamic_friction": float(dynamic_friction),
                "collisions": bool(collisions),
            },
            prompt="Use create_gravity_field and connect_dynamic_field for forces, then maya-animation bake_simulation.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create rigid bodies")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`make_rigid_body`."""
    return make_rigid_body(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
