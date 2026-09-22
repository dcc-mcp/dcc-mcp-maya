"""Combine two or more sources into a single comp output."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import MERGE_OPS, CompositingContractError
from dcc_mcp_maya.compositing import merge_layers as _merge_layers


def merge_comp_layers(
    sources: Optional[List[str]] = None,
    operation: str = "blend",
    name: Optional[str] = None,
    blend_amount: float = 0.5,
) -> dict:
    """Merge sources with a blend or a layered blend mode."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _merge_layers(
            cmds,
            sources=sources or [],
            operation=operation,
            name=name,
            blend_amount=blend_amount,
        )
        return maya_success(
            "Merged {} source(s) with {}".format(len(result["sources"]), result["operation"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid comp merge request",
            str(exc),
            possible_solutions=[
                "operation must be one of: " + ", ".join(MERGE_OPS),
                "blend takes exactly two sources; use a layered operation for more.",
                "Every source must exist and expose an outColor plug.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to merge comp layers")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`merge_comp_layers`."""
    return merge_comp_layers(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
