"""Perform a bounded action on a Maya Qt widget."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya import _dev_session


@skill_entry
def main(**kwargs) -> dict:
    return _dev_session.ui_action(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
