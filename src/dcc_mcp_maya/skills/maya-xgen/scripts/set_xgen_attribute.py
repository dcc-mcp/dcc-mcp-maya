"""Set an attribute on an XGen description or modifier."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


def set_xgen_attribute(
    collection: str,
    description: str,
    attribute: str,
    value: str,
    object_name: str = "",
) -> dict:
    """Set an XGen attribute value.

    Args:
        collection: XGen collection name.
        description: Description name.
        attribute: Attribute name (e.g. "density", "length").
        value: New value as string (XGen uses string-based attrs).
        object_name: Object context for patch attributes (optional).

    Returns:
        ActionResultModel dict.
    """
    try:
        import xgenm as xg  # noqa: PLC0415

        xg.setAttr(attribute, str(value), collection, description, object_name)
        return skill_success(
            "Set {}.{} = {}".format(description, attribute, value),
            prompt="Use get_xgen_attribute to verify the change.",
            collection=collection,
            description=description,
            attribute=attribute,
            value=str(value),
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to set XGen attribute")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_xgen_attribute`."""
    return set_xgen_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
