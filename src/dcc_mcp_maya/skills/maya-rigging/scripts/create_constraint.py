"""Create common Maya rig constraints."""

from __future__ import annotations

from typing import List, Optional, Union

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success


def _as_list(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def create_constraint(
    drivers: Union[str, List[str]],
    driven: str,
    constraint_type: str = "parent",
    maintain_offset: bool = True,
    weight: float = 1.0,
    name: Optional[str] = None,
    aim_vector: Optional[List[float]] = None,
    up_vector: Optional[List[float]] = None,
) -> dict:
    """Create a parent, point, orient, scale, aim, or pole-vector constraint."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        driver_names = _as_list(drivers)
        if not driver_names:
            return maya_error("No drivers provided", "drivers must contain at least one node.")
        err = batch_validate_nodes(cmds, driver_names + [driven])
        if err:
            return err

        kwargs = {"weight": float(weight)}
        if name:
            kwargs["name"] = str(name)
        if constraint_type != "pole_vector":
            kwargs["maintainOffset"] = bool(maintain_offset)

        if constraint_type == "parent":
            result = cmds.parentConstraint(*driver_names, driven, **kwargs)
        elif constraint_type == "point":
            result = cmds.pointConstraint(*driver_names, driven, **kwargs)
        elif constraint_type == "orient":
            result = cmds.orientConstraint(*driver_names, driven, **kwargs)
        elif constraint_type == "scale":
            result = cmds.scaleConstraint(*driver_names, driven, **kwargs)
        elif constraint_type == "aim":
            if aim_vector is not None:
                kwargs["aimVector"] = tuple(float(item) for item in aim_vector)
            if up_vector is not None:
                kwargs["upVector"] = tuple(float(item) for item in up_vector)
            result = cmds.aimConstraint(*driver_names, driven, **kwargs)
        elif constraint_type == "pole_vector":
            result = cmds.poleVectorConstraint(*driver_names, driven, **kwargs)
        else:
            return maya_error(
                "Unsupported constraint type",
                "constraint_type must be parent, point, orient, scale, aim, or pole_vector.",
            )

        constraints = [str(item) for item in (result or [])]
        return maya_success(
            "Created {} constraint on {}".format(constraint_type, driven),
            constraint_type=constraint_type,
            drivers=driver_names,
            driven=driven,
            constraints=constraints,
            maintain_offset=bool(maintain_offset),
            weight=float(weight),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create rig constraint")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_constraint`."""
    return create_constraint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
