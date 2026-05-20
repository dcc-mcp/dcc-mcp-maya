"""Hot-reload modules from an attached Maya tool development project."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya import _dev_session


@skill_entry
def main(**kwargs) -> dict:
    return _dev_session.reload_modules(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
