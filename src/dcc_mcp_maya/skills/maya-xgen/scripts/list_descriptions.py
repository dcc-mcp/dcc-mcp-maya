"""List all XGen descriptions in the scene."""
from dcc_mcp_core import error_result, success_result


def run(params):
    """List XGen descriptions, optionally filtered by collection.

    Args:
        params: dict with keys:
            - collection (str, optional): Limit results to this collection.

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds  # noqa: F401 — ensure maya is importable

    try:
        import xgenm as xg

        collection_filter = params.get("collection")
        palettes = xg.palettes()
        result = []
        for palette in palettes:
            if collection_filter and palette != collection_filter:
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

        return success_result(
            "Found {} XGen description(s)".format(len(result)),
            prompt="Use set_xgen_attribute to modify description parameters.",
            descriptions=result,
            count=len(result),
        )
    except Exception as exc:
        return error_result(
            "Failed to list XGen descriptions",
            str(exc),
            prompt="Ensure XGen plugin is loaded: cmds.loadPlugin('xgenToolkit').",
        )
