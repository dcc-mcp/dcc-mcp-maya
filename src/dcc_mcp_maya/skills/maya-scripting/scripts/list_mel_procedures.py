"""List MEL global procedures matching an optional pattern."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


def list_mel_procedures(pattern: str = "", limit: int = 200) -> dict:
    """List MEL global procedures, optionally filtered by a substring pattern.

    Args:
        pattern: Substring filter applied to procedure names (case-insensitive).
            Default ``""`` (return all procedures).
        limit: Maximum number of results to return. Default 200.

    Returns:
        ActionResultModel dict with ``context.procedures`` list and ``context.count``.
    """

    try:
        import maya.mel as mel  # noqa: PLC0415

        # Warm-up call (result unused)
        mel.eval('whatIs ""')
        # globalProcs() returns a MEL string array.
        # In mayapy standalone, it may not be available — return empty list in that case.
        try:
            procs = mel.eval("globalProcs()")
            if not isinstance(procs, list):
                procs = []
        except Exception:
            procs = []

        lower_pattern = pattern.lower()
        if lower_pattern:
            procs = [p for p in procs if lower_pattern in p.lower()]

        procs = sorted(procs)[: int(limit)]

        return skill_success(
            "Found {} MEL procedures".format(len(procs)),
            prompt="Procedures listed. Use execute_mel to call any of them.",
            procedures=procs,
            count=len(procs),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.mel could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list MEL procedures")


@skill_entry
def main(**kwargs):
    return list_mel_procedures(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
