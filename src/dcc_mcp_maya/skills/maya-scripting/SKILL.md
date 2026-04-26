---
name: maya-scripting
description: "Primary fall-through entry point for arbitrary Maya work. When no domain skill matches, load this skill and call execute_python or execute_mel. Includes API introspection tools for discovering maya.cmds flags and OpenMaya signatures without leaving the agent loop."
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 2.0.0
    tags:
    - maya
    - scripting
    - mel
    - python
    - introspect
    search-hint: fallthrough, no-matching-tool, write-custom, arbitrary-task, run script, MEL Python, custom automation, inspect api, cmds help
    depends: []
    tools: tools.yaml
    groups: groups.yaml
    recipes: references/RECIPES.md
    introspection: references/INTROSPECTION.md
---
# maya-scripting

Primary **fall-through** skill. When no domain skill matches a user request,
load this skill and call `execute_python` or `execute_mel` directly.

This follows the Bitter Lesson: LLMs already know `maya.cmds` and `OpenMaya`
from training data. A thin harness with good error messages lets agents
self-heal better than wrapping every API in a named helper.

**Decision tree:**

```
Intent matches a domain skill (shot-export, render-farm, pipeline)?
  → load that skill instead.
Anything else (geometry, materials, animation, rigging, …)?
  → load maya-scripting, read RECIPES.md, call execute_python.
Unsure of flag name or method signature?
  → activate introspect group, call introspect_signature / introspect_search.
```

## Groups

- **core** (`default_active: true`) — `execute_mel`, `execute_python`,
  `list_mel_procedures`, `get_script_node`. Always loaded.
- **introspect** (`default_active: false`) — API introspection tools.
  Load with `activate_group("introspect")`. See `references/INTROSPECTION.md`.

## Scripts

- `execute_python` — Execute arbitrary Python inside Maya's interpreter
- `execute_mel` — Execute a MEL script inside Maya
- `list_mel_procedures` — List available MEL global procedures
- `get_script_node` — Inspect a Maya scriptNode's content
- `introspect_list_module` — List public names in maya.cmds / OpenMaya (paginated)
- `introspect_signature` — Return flag list / method signature for a Maya API name
- `introspect_search` — Case-insensitive search over module names and flag names
- `introspect_eval` — Evaluate a read-only Python expression inside Maya (main-thread)
