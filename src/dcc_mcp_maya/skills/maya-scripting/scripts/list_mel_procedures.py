"""List MEL global procedures matching an optional pattern."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_mel_procedures(pattern: str = "", limit: int = 200) -> dict:
    """List MEL global procedures, optionally filtered by a substring pattern.

    Args:
        pattern: Substring filter applied to procedure names (case-insensitive).
            Default ``""`` (return all procedures).
        limit: Maximum number of results to return. Default 200.

    Returns:
        ActionResultModel dict with ``context.procedures`` list and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} MEL procedures".format(len(procs)),
            prompt="Procedures listed. Use execute_mel to call any of them.",
            procedures=procs,
            count=len(procs),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.mel could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_mel_procedures failed")
        return error_result("Failed to list MEL procedures", str(exc)).to_dict()


def main(**kwargs):
    return list_mel_procedures(**kwargs)


if __name__ == "__main__":
    import json

    result = list_mel_procedures(pattern="poly", limit=20)
    print(json.dumps(result))
