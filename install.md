# dcc-mcp-maya Agent Install

Use this page when an agent is asked to install or configure
`loonghao/dcc-mcp-maya` for Autodesk Maya.

## Agent Instruction

If the user says "帮我参考 loonghao/dcc-mcp-maya/install.md 去安装",
do this:

1. Read `skills/dcc-mcp-maya-setup/SKILL.md`.
2. Run the setup script from the repository root.
3. Help the user load the Maya plugin in Plug-in Manager.
4. Configure the MCP host with the generated Streamable HTTP JSON.
5. Run the smoke prompt to prove the connection works.

## One Command

From the repository root:

```bash
python skills/dcc-mcp-maya-setup/scripts/setup_dcc_mcp_maya.py
```

For an end-user install from PyPI instead of this checkout:

```bash
python skills/dcc-mcp-maya-setup/scripts/setup_dcc_mcp_maya.py --source pypi
```

If `mayapy` is not auto-detected:

```bash
python skills/dcc-mcp-maya-setup/scripts/setup_dcc_mcp_maya.py --mayapy "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
```

## Maya Plugin Step

After the script finishes, the user must open Maya and load the plugin:

1. Open `Window > Settings/Preferences > Plug-in Manager`.
2. Find or add `maya/plugin/dcc_mcp_maya_plugin.py`.
3. Enable `Loaded`.
4. Enable `Auto load` if this should start with Maya.

Plugin sidecar mode usually exposes MCP at:

```text
http://127.0.0.1:9765/mcp
```

Manual `start_server(port=8765)` mode uses:

```text
http://127.0.0.1:8765/mcp
```

## MCP Config

Use this JSON for Cursor, Claude Desktop, or any MCP Streamable HTTP host:

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

The setup script also writes config snippets and a smoke prompt under:

```text
.dcc-mcp/agent-setup/
```
