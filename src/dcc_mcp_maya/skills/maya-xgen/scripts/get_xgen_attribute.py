"""Get an attribute value from an XGen description."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


def get_xgen_attribute(
    collection: str,
    description: str,
    attribute: str,
    object_name: str = "",
) -> dict:
    """Get an XGen attribute value.

    Args:
        collection: XGen collection name.
        description: Description name.
        attribute: Attribute name.
        object_name: Object context (optional).

    Returns:
        ActionResultModel dict with ``context.value``.
    """
    try:
        import xgenm as xg  # noqa: PLC0415

        value = xg.getAttr(attribute, collection, description, object_name)
        return skill_success(
            "{}.{} = {}".format(description, attribute, value),
            prompt="Use set_xgen_attribute to modify this value.",
            collection=collection,
            description=description,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to get XGen attribute")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_xgen_attribute`."""
    return get_xgen_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
