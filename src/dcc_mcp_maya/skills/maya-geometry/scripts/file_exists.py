"""Check whether a file exists."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from pathlib import Path

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


def file_exists(path: str) -> dict:
    if not path:
        return skill_error("Missing path", "path is required")
    exists = Path(path).exists()
    return skill_success("File exists" if exists else "File does not exist", path=path, exists=exists)


@skill_entry
def main(**kwargs) -> dict:
    return file_exists(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
