# Advanced Usage

## Custom Skills

The easiest way to extend `dcc-mcp-maya` is to create a custom skill — a directory containing a `SKILL.md` descriptor and Python action scripts.

### Skill Directory Structure

```
my-studio-tools/
├── SKILL.md
└── scripts/
    ├── setup_shot.py
    ├── export_alembic.py
    └── validate_naming.py
```

### SKILL.md Format

```yaml
---
name: my-studio-tools
description: "Studio-specific pipeline automation for Hero Studio"
dcc: maya
version: "1.0.0"
tags: [maya, pipeline, studio]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# my-studio-tools

## Scripts

- `setup_shot` — Set up a new shot from the shot template
- `export_alembic` — Export character cache as Alembic
- `validate_naming` — Validate object naming conventions
```

### Action Script Format

Each script in `scripts/` becomes one MCP action. The script must define a function with the same name as the file:

```python
# scripts/setup_shot.py
"""Set up a new Maya shot from the studio template."""


def setup_shot(shot_name: str, frame_range: list = None) -> dict:
    """Set up a new shot by importing the template scene and configuring it.

    Args:
        shot_name: The shot identifier, e.g. "SH_0010"
        frame_range: [start, end] frame range. Defaults to [1001, 1100].

    Returns:
        dict with keys: success (bool), shot_name (str), message (str)
    """
    import maya.cmds as cmds

    if frame_range is None:
        frame_range = [1001, 1100]

    # Import template
    template_path = "/pipeline/templates/shot_template.ma"
    cmds.file(template_path, i=True, type="mayaAscii", ignoreVersion=True)

    # Configure timeline
    cmds.playbackOptions(min=frame_range[0], max=frame_range[1])
    cmds.playbackOptions(animationStartTime=frame_range[0], animationEndTime=frame_range[1])

    # Rename root group
    if cmds.objExists("SHOT_TEMPLATE"):
        cmds.rename("SHOT_TEMPLATE", shot_name)

    return {
        "success": True,
        "shot_name": shot_name,
        "message": f"Shot {shot_name} set up with frames {frame_range[0]}-{frame_range[1]}",
    }
```

### Registering Your Skill

**Option A — Environment variable:**
```bash
# Windows
set DCC_MCP_MAYA_SKILL_PATHS=C:\studio\maya-skills

# macOS/Linux
export DCC_MCP_MAYA_SKILL_PATHS=/studio/maya-skills
```

**Option B — Pass at startup:**
```python
import dcc_mcp_maya
handle = dcc_mcp_maya.start_server(
    extra_skill_paths=["C:/studio/maya-skills"]
)
```

**Option C — Multiple paths:**
```bash
set DCC_MCP_MAYA_SKILL_PATHS=C:\studio\tools;C:\shared\pipeline-skills
```

### Verifying Registration

```python
from dcc_mcp_maya.server import MayaMcpServer
server = MayaMcpServer()
server.register_builtin_actions(extra_skill_paths=["C:/studio/maya-skills"])
# Check registered tools
for skill in server._server.list_skills():
    print(skill.name)
```

## MayaMcpServer API

For programmatic control:

```python
from dcc_mcp_maya.server import MayaMcpServer

# Create with custom config
server = MayaMcpServer(
    port=9000,
    server_name="my-maya-studio",
    server_version="2.0.0",
)

# Load only specific skill paths
server.register_builtin_actions(
    extra_skill_paths=["/studio/skills"]
)

# Start
handle = server.start()
print(f"Running at {handle.mcp_url()}")
print(f"Port: {handle.port}")

# Check status
if server.is_running:
    print("Server is running")

# Stop
server.stop()
```

## Main Thread Safety

Maya's API is **not thread-safe** — all `maya.cmds` and `OpenMaya` calls must happen on the main thread.

`dcc-mcp-maya` handles this automatically:

1. The HTTP server runs on a **Tokio worker thread** (inside `dcc-mcp-core`)
2. When an action is called, it is dispatched to Maya's main thread via `maya.utils.executeDeferred`
3. A poll callback installed via `maya.utils.executeDeferred` drains the pending queue on every UI tick

This means:
- Actions are safe to use even from multi-threaded AI host connections
- You don't need to add any thread guards in your action scripts
- Long-running operations will occupy the main thread until complete

## Skill Discovery Search Path

Skills are discovered in this priority order (highest to lowest):

1. `extra_skill_paths` passed to `start_server()` or `register_builtin_actions()`
2. Built-in `skills/` directory shipped in this package
3. `DCC_MCP_MAYA_SKILL_PATHS` environment variable (Maya-specific)
4. `DCC_MCP_SKILL_PATHS` environment variable (global fallback)
5. Platform default skills directory (`dcc_mcp_core.get_skills_dir()`)

## Hot-Reload During Development

When developing custom skills, you can enable the skill watcher for hot-reload (requires `dcc-mcp-core >= 0.12.10`):

```python
from dcc_mcp_core import McpHttpServer, ActionRegistry, McpHttpConfig

config = McpHttpConfig(port=8765, server_name="maya-dev")
registry = ActionRegistry()
server = McpHttpServer(registry, config)

# Enable file watcher
server.discover(extra_paths=["/studio/my-skill"], dcc_name="maya")
server.enable_skill_watcher(True)  # hot-reload on file change
handle = server.start()
```

## Logging

Enable debug logging to trace action calls:

```python
import logging
logging.getLogger("dcc_mcp_maya").setLevel(logging.DEBUG)
logging.getLogger("dcc_mcp_core").setLevel(logging.DEBUG)
```

Output goes to Maya's `Output Window` / Script Editor console.

## Plugin Mode

See [Installation — Method 2](/guide/installation#method-2-maya-plugin) for loading as a Maya plugin. The plugin reads `DCC_MCP_MAYA_PORT` from the environment at load time.

To configure the port before loading the plugin:

```python
import os
os.environ["DCC_MCP_MAYA_PORT"] = "9000"

import maya.cmds as cmds
cmds.loadPlugin("dcc_mcp_maya")
```
