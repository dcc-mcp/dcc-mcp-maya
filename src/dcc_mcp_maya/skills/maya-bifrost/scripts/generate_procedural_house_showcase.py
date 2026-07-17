"""Stage a deterministic four-style Bifrost house showcase."""

from __future__ import annotations

from typing import Optional, Sequence

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import ensure_bifrost_plugins
from dcc_mcp_maya.procedural_house_showcase import build_house_showcase, design_house_showcase


def generate_procedural_house_showcase(
    seed: Optional[int] = None,
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    spacing: float = 9.0,
    frame_count: int = 72,
    replace: bool = True,
) -> dict:
    """Build a staged and animated house showcase in the current scene."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        spec = design_house_showcase(
            seed=seed,
            name=name,
            position=position,
            spacing=spacing,
            frame_count=frame_count,
        )
        showcase = build_house_showcase(cmds, spec, replace=replace)
        return maya_success(
            "Generated four-style Bifrost house showcase with seed {}".format(spec.seed),
            runtime=runtime,
            **showcase,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to generate procedural Bifrost house showcase")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`generate_procedural_house_showcase`."""
    return generate_procedural_house_showcase(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
