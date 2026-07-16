# Standalone mayapy MCP example

Use this example when you want a headless Maya process to expose MCP without
opening the Maya GUI.

## Run

Install into the target Maya Python first:

```bash
mayapy -m pip install "dcc-mcp-maya[sidecar]"
```

Start the standalone service:

```bash
mayapy examples/standalone/run_maya_mcp.py
```

The instance port is assigned by the operating system. The script prints the
exact MCP URL after startup, for example:

```text
[dcc-mcp-maya] standalone MCP: http://127.0.0.1:<assigned-port>/mcp
```

Point a direct Streamable HTTP MCP host at the printed URL. For normal plugin
deployments, use the stable gateway at `http://127.0.0.1:9765/mcp` and inspect
instances with `dcc-mcp-cli list` instead of hardcoding an instance port.

## Custom skill example

This directory includes a headless-safe skill under
`custom-skills/standalone-scene-report`.

Run the service with that skill path enabled:

```bash
# Windows PowerShell
$env:DCC_MCP_MAYA_SKILL_PATHS = "$PWD\examples\standalone\custom-skills"
mayapy examples/standalone/run_maya_mcp.py
```

Then ask your MCP host:

```text
Load the standalone-scene-report skill and call standalone_scene_report__create_report_cube.
```

The skill imports `maya.cmds` inside the tool function, declares
`affinity: main`, and avoids UI-only commands so it works in `mayapy` /
`maya.standalone`.
