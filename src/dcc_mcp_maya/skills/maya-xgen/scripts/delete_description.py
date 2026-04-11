"""Delete an XGen description from the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def delete_description(
    collection: str,
    description: str,
) -> dict:
    """Delete an XGen description by collection and description name.

    Args:
        collection: XGen collection name.
        description: Description name to delete.

    Returns:
        ActionResultModel dict.
    """
    try:
        import xgenm as xg  # noqa: PLC0415

        if description not in xg.descriptions(collection):
            return skill_error(
                "Description not found",
                "'{}' not found in collection '{}'".format(description, collection),
                prompt="Use list_descriptions to view available descriptions.",
            )

        xg.deleteDescription(collection, description)
        return skill_success(
            "Deleted XGen description '{}'".format(description),
            prompt="Use list_descriptions to verify deletion.",
            collection=collection,
            description=description,
        )
    except ImportError:
        return skill_error("XGen not available", "xgenm could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete XGen description")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_description`."""
    return delete_description(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
