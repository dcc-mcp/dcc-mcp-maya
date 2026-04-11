"""List MEL global procedures matching an optional pattern."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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
        # globalProcs() returns a MEL string array
        procs = mel.eval("globalProcs()")
        if not isinstance(procs, list):
            procs = []

        lower_pattern = pattern.lower()
        if lower_pattern:
            procs = [p for p in procs if lower_pattern in p.lower()]

        procs = sorted(procs)[: int(limit)]

        return maya_success(
            "Found {} MEL procedures".format(len(procs)),
            prompt="Procedures listed. Use execute_mel to call any of them.",
            procedures=procs,
            count=len(procs),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.mel could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to list MEL procedures")

def main(**kwargs):
    return list_mel_procedures(**kwargs)

if __name__ == "__main__":
    import json

    result = list_mel_procedures(pattern="poly", limit=20)
    print(json.dumps(result))
