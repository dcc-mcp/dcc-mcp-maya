# Contributing a Custom Skill

`dcc-mcp-maya` is designed to be extended. You can ship your own skill packages
alongside the built-ins — without touching the core package.

## Skill Package Layout

A skill is a directory with the following structure:

```
my-skill/
├── SKILL.md          ← required skill manifest
└── scripts/
    ├── do_something.py
    └── get_info.py
```

Each `.py` file in `scripts/` becomes one MCP tool automatically.

## Writing an Action Script

Every script must expose a **top-level function whose name matches the file stem**:

```python
# scripts/create_locator_grid.py
"""Create a grid of locators at evenly-spaced positions."""

from __future__ import annotations
from typing import Optional


def create_locator_grid(
    rows: int = 3,
    cols: int = 3,
    spacing: float = 2.0,
    name_prefix: Optional[str] = "loc",
) -> dict:
    """Create a grid of locators.

    Args:
        rows: Number of rows.
        cols: Number of columns.
        spacing: Distance between locators in scene units.
        name_prefix: Prefix for locator names.

    Returns:
        ActionResultModel dict with ``context.locators`` list.
    """
    # Always lazy-import maya.cmds to allow skill discovery outside Maya
    import maya.cmds as cmds
    from dcc_mcp_core import success_result, error_result

    try:
        locators = []
        for r in range(rows):
            for c in range(cols):
                loc = cmds.spaceLocator(
                    name=f"{name_prefix}_{r}_{c}",
                    position=(c * spacing, 0, r * spacing),
                )[0]
                locators.append(loc)

        return success_result(
            f"Created {len(locators)} locators",
            locators=locators,
            count=len(locators),
        ).to_dict()
    except Exception as exc:
        return error_result("Failed to create locator grid", str(exc)).to_dict()


def main(**kwargs):
    return create_locator_grid(**kwargs)
```

### Key rules

| Rule | Why |
|------|-----|
| Lazy-import `maya.cmds` **inside** the function | Skills are discovered without a running Maya |
| Return a `dict` (use `dcc_mcp_core.success_result` / `error_result`) | Consistent MCP response format |
| Function name = file stem | Auto-registration relies on this convention |
| Module docstring = MCP tool description | Shown to the AI in the tool list |

## Registering Your Skill

### Option 1 — Environment variable

Point `DCC_MCP_MAYA_SKILL_PATHS` (or `DCC_MCP_SKILL_PATHS`) at the **parent
directory** of your skill folders:

```
my-skills/
├── my-skill/
│   └── scripts/
└── another-skill/
    └── scripts/
```

```bash
# Windows PowerShell
$env:DCC_MCP_MAYA_SKILL_PATHS = "C:\Users\me\my-skills"
```

```python
# Or set it before starting the server
import os
os.environ["DCC_MCP_MAYA_SKILL_PATHS"] = r"C:\Users\me\my-skills"

import dcc_mcp_maya
dcc_mcp_maya.start_server()
```

### Option 2 — Pass paths directly

```python
import dcc_mcp_maya

dcc_mcp_maya.start_server(
    extra_skill_paths=[r"C:\Users\me\my-skills"]
)
```

### Option 3 — Place inside the built-in skills directory

For permanent additions, copy your skill folder into the installed package:

```
<site-packages>/dcc_mcp_maya/skills/my-skill/
```

> **Note:** This approach will be lost on package upgrades. Prefer env vars for
> development and option 2 for production deployments.

## Naming Convention

The MCP tool name is derived automatically:

```
{skill_dir_name.replace("-", "_")}__{script_file_stem}
```

Examples:

| Skill dir | Script file | MCP tool name |
|-----------|-------------|---------------|
| `my-skill` | `do_something.py` | `my_skill__do_something` |
| `studio-pipeline` | `publish_asset.py` | `studio_pipeline__publish_asset` |

## Testing Your Action Locally

You can run an action script directly from a Python shell **without Maya** to
verify its structure:

```python
import importlib.util, pathlib

spec = importlib.util.spec_from_file_location(
    "create_locator_grid",
    pathlib.Path("my-skill/scripts/create_locator_grid.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Check the function exists and signature is correct
import inspect
print(inspect.signature(mod.create_locator_grid))
```

For a full end-to-end test, use the `dcc_execute_action` MCP tool from your AI
host after registering the skill.

## Checklist Before Sharing

- [ ] Module-level docstring is concise and descriptive (shown to the AI)
- [ ] All parameters have type annotations and docstring entries
- [ ] `maya.cmds` is imported lazily inside the function
- [ ] Returns `success_result(…).to_dict()` on success
- [ ] Returns `error_result(…).to_dict()` on known error conditions
- [ ] `main(**kwargs)` wrapper is present
- [ ] Tested with `vitepress build` if adding docs
