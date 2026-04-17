"""List all XGen descriptions in the scene."""

# Import future modules
from __future__ import annotations

from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


def list_descriptions(collection: Optional[str] = None) -> dict:
    """List XGen descriptions, optionally filtered by collection.

    Args:
        collection: Limit results to this collection. Lists all collections
            when omitted.

    Returns:
        ToolResult dict with ``context.descriptions`` and ``context.count``.
    """
    try:
        import xgenm as xg  # noqa: PLC0415

        palettes = xg.palettes()
        result = []
        for palette in palettes:
            if collection and palette != collection:
                continue
            for desc in xg.descriptions(palette):
                bound = list(xg.boundGeometry(palette, desc))
                result.append(
                    {
                        "collection": palette,
                        "description": desc,
                        "bound_geometry": bound,
                    }
                )

        return skill_success(
            "Found {} XGen description(s)".format(len(result)),
            prompt="Use set_xgen_attribute to modify description parameters.",
            descriptions=result,
            count=len(result),
        )
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to list XGen descriptions",
            prompt="Ensure XGen plugin is loaded: cmds.loadPlugin('xgenToolkit').",
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_descriptions`."""
    return list_descriptions(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
