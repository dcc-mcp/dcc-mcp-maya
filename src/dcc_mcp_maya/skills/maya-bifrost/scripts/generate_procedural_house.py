"""Generate a deterministic multi-style house as an evaluated Bifrost graph."""

from __future__ import annotations

from typing import Optional, Sequence

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import ensure_bifrost_plugins
from dcc_mcp_maya.procedural_house import build_house_graph, design_house


def generate_procedural_house(
    seed: Optional[int] = None,
    style: str = "random",
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
) -> dict:
    """Build one seed-driven house in the current Maya scene."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        spec = design_house(seed=seed, style=style, position=position)
        house = build_house_graph(cmds, spec, name=name)
        if house.get("transform"):
            cmds.select(house["transform"], replace=True)
        return maya_success(
            "Generated {} Bifrost house with seed {}".format(spec.style, spec.seed),
            runtime=runtime,
            **house,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to generate procedural Bifrost house")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`generate_procedural_house`."""
    return generate_procedural_house(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
