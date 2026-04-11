"""Execute a MEL script inside Maya."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


def execute_mel(script: str) -> dict:
    """Execute a MEL expression and return its string result.

    Args:
        script: MEL code to execute.

    Returns:
        ActionResultModel dict with ``context.output`` (str) and ``context.script``.
    """

    if not script or not script.strip():
        return skill_error("No MEL code provided", "Provide 'script' with valid MEL.")

    try:
        import maya.mel as mel  # noqa: PLC0415

        raw = mel.eval(script)
        output = str(raw) if raw is not None else ""
        return skill_success(
            "MEL executed successfully",
            prompt="MEL script finished. Check 'output' for any return value.",
            output=output,
            script=script,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.mel could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="MEL execution failed")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_mel`."""
    return execute_mel(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
