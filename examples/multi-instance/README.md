# Multi-instance example

A drop-in `userSetup.py` for running multiple Maya instances on a single
workstation, all discoverable through a single MCP gateway.

## Install

Copy `userSetup.py` to your Maya scripts directory (or `source` it from
your existing `userSetup.py`):

- Windows: `%USERPROFILE%/Documents/maya/scripts/userSetup.py`
- macOS:   `~/Library/Preferences/Autodesk/maya/scripts/userSetup.py`
- Linux:   `~/maya/scripts/userSetup.py`

## What it does

On every Maya launch:

1. Leaves the instance port unset so `dcc-mcp-core` binds port `0`; the
   operating system assigns a free port atomically and the exact URL is
   published to discovery.
2. Exports `DCC_MCP_MAYA_DCC_PID=<os.getpid()>` so `diagnostics__*`
   tools route to the correct Maya.
3. Exports `DCC_MCP_GATEWAY_PORT=9765` so every instance shares the
   same gateway election.
4. Loads the `dcc_mcp_maya_plugin` via `executeDeferred`.

The `apply_multi_instance_env` helper is unit-tested in
`tests/test_multi_instance_example.py`; see the full
deployment guide at
[`docs/guide/multi-instance.md`](../../docs/guide/multi-instance.md).
