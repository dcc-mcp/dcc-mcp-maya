---
name: dcc-mcp-maya-setup
description: |-
  Set up dcc-mcp-maya for an agent or operator: install Maya Python
  dependencies with mayapy, generate MCP host configuration, guide the user
  through loading the Maya plugin, and run a first live-tool smoke prompt.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: operator
    stage: bootstrap
    version: 1.0.0
    tags:
    - maya
    - mcp
    - setup
    - mayapy
    - plugin
---
# dcc-mcp-maya setup

Use this skill when a user wants an agent to prepare a machine so any MCP
host can use `dcc-mcp-maya` with Autodesk Maya.

This is an operator skill, not a Maya runtime skill. Do not load it through
the Maya MCP server. Run it from the repository checkout or copy its steps into
another agent's instructions.

If the user says "帮我参考 `loonghao/dcc-mcp-maya/install.md` 去安装", read the
root `install.md` first, then follow this skill.

## Goal

End with:

- `dcc-mcp-maya` and its pip dependencies installed into the target Maya
  `mayapy` environment.
- An MCP host config snippet that points to the Maya plugin gateway.
- The user guided to load `dcc_mcp_maya_plugin.py` in Maya's Plug-in Manager.
- A live smoke prompt that proves the agent can discover and call Maya tools.

## Fast Path

From the repository root, run:

```bash
python skills/dcc-mcp-maya-setup/scripts/setup_dcc_mcp_maya.py
```

The script:

1. Finds `mayapy` from `--mayapy`, `MAYAPY`, `DCC_MCP_MAYA_MAYAPY`, `PATH`,
   or common Autodesk install locations.
2. Installs this checkout into Maya with the sidecar extra:
   `mayapy -m pip install -e ".[sidecar]"`.
3. Verifies `import dcc_mcp_maya`.
4. Writes reusable MCP JSON snippets under `.dcc-mcp/agent-setup/`.

Use PyPI instead of the local checkout when setting up an end-user machine:

```bash
python skills/dcc-mcp-maya-setup/scripts/setup_dcc_mcp_maya.py --source pypi
```

If discovery fails, ask the user for the full `mayapy` path and re-run:

```bash
python skills/dcc-mcp-maya-setup/scripts/setup_dcc_mcp_maya.py --mayapy "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
```

## MCP Configuration

Plugin sidecar mode is the preferred default. Configure the MCP host with:

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

Use `http://127.0.0.1:8765/mcp` only when the user explicitly starts the
server manually with `dcc_mcp_maya.start_server(port=8765)`.

When editing an existing MCP config, preserve unrelated servers. Merge only the
`maya` server entry unless the user asks for a different server name.

## User Hand-Off: Load the Maya Plugin

After pip setup and MCP JSON generation, tell the user:

1. Open Autodesk Maya.
2. Go to `Window > Settings/Preferences > Plug-in Manager`.
3. Add or find `dcc_mcp_maya_plugin.py`.
4. Check `Loaded`; optionally check `Auto load`.
5. Watch Script Editor output for the MCP URL.

Expected plugin-mode URL is usually `http://127.0.0.1:9765/mcp`.

If the plugin is not visible, verify that `maya/plugin/dcc_mcp_maya_plugin.py`
is on `MAYA_PLUG_IN_PATH` or copy it into the user's Maya plug-ins folder.

## First Live Smoke Prompt

Ask the MCP host to run this prompt after Maya is open and the plugin is
loaded:

```text
Use the Maya MCP server. First call dcc_capability_manifest with loaded_only=false.
Then load the maya-primitives skill, create a sphere named mcp_setup_smoke_sphere
with radius 2, list scene objects, and tell me the MCP URL and created object name.
Use typed tools where available and avoid execute_python unless no typed tool fits.
```

Expected behavior:

- The agent discovers capabilities without dumping every schema.
- The agent loads `maya-primitives`.
- The agent calls `maya_primitives__create_sphere`.
- The new object appears in the Maya scene.
- `maya_scene__list_objects` or another scene query confirms it exists.

## Troubleshooting

- `mayapy` not found: ask for the exact Maya version and mayapy path.
- Pip bootstrap fails: run `mayapy -m ensurepip --upgrade`, then repeat install.
- MCP connection refused: Maya is not running, the plugin is not loaded, or the
  host is pointing at `8765` while plugin sidecar mode is on `9765`.
- Tool missing: call `dcc_capability_manifest` or `search_skills`, then
  `load_skill("<skill-name>")`.
- Plugin loaded but hangs: check Script Editor output, firewall/localhost
  rules, and whether a blocking Maya dialog is open.
