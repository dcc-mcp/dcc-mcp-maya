"""Connect a source into the next free layer of a comp stack."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import BLEND_MODES, CompositingContractError
from dcc_mcp_maya.compositing import add_layer as _add_layer


def add_comp_layer(
    stack: Optional[str] = None,
    source: Optional[str] = None,
    blend_mode: str = "None",
    opacity: float = 1.0,
    visible: bool = True,
) -> dict:
    """Add one layer to a stack."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _add_layer(
            cmds,
            stack=stack or "",
            source=source or "",
            blend_mode=blend_mode,
            opacity=opacity,
            visible=visible,
        )
        return maya_success(
            "Added {} to {} at layer {}".format(result["source"], result["stack"], result["index"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid comp layer request",
            str(exc),
            possible_solutions=[
                "stack must be a layeredTexture; create one with create_layer_stack.",
                "blend_mode must be one of: " + ", ".join(BLEND_MODES),
                "source must exist and expose an outColor plug.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to add comp layer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_comp_layer`."""
    return add_comp_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
