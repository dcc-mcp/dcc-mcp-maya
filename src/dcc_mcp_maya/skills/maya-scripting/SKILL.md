---
name: maya-scripting
description: |-
  Bootstrap stage — primary fall-through for arbitrary Maya work. Load this when
  no domain skill matches the user intent and you need to drive maya.cmds /
  OpenMaya directly through execute_python or execute_mel. Includes API
  introspection tools so an agent can discover flags and method signatures
  without leaving the loop.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: thin-harness
    stage: bootstrap
    version: 2.1.0
    tags:
    - maya
    - scripting
    - mel
    - python
    - introspect
    search-hint: |-
      fallthrough, no-matching-tool, write-custom, arbitrary-task, run script,
      MEL Python, custom automation, inspect api, cmds help, signature,
      flag list
    aliases:
    - maya-script
    - maya-fallthrough
    side-effects:
    - executes-arbitrary-code
    - reads-scene
    - writes-scene
    depends: []
    tools: tools.yaml
    groups: groups.yaml
    recipes: references/RECIPES.md
    introspection: references/INTROSPECTION.md
---
# maya-scripting (Bootstrap stage)

Primary **fall-through** skill. When no domain skill matches a user request,
load this skill and call `execute_python` or `execute_mel` directly.

This follows the Bitter Lesson: LLMs already know `maya.cmds` and `OpenMaya`
from training data. A thin harness with good error messages lets agents
self-heal better than wrapping every API in a named helper.

## Decision tree

```
Intent matches a Pipeline-stage skill (shot-export, render-farm, pipeline)?
  → load that skill instead.
Intent matches an Interchange skill (FBX/OBJ/preset import or export)?
  → load maya-geometry / maya-export-preset.
Intent matches an Authoring skill (mesh, uv, material, rig, anim, light)?
  → load that domain skill — its tools.yaml has full inputSchema and safety hints.
Anything else?
  → load maya-scripting, read RECIPES.md, call execute_python.
Unsure of flag name or method signature?
  → activate the introspect group, call introspect_signature / introspect_search.
```

## Why this skill is special

- It is the **only** stage = `bootstrap` skill. The minimal-mode default
  loads it eagerly so an agent always has a reachable escape hatch.
- Every dispatched job runs inside `dcc_mcp_maya._safe_session.mcp_safe_session`,
  so even an `execute_python` body that calls `cmds.confirmDialog` or triggers
  Maya's AutoSave save-prompt will not deadlock the dispatcher.

## Dynamics / solver safety (host crashes)

Legacy **`cmds.rigidBody` + `cmds.gravity`** snippets from older tutorials are a
frequent source of **fatal Maya exits** when driven from MCP / batch contexts
(the solver stack is not fully re-entrant with arbitrary evaluation order).
Prefer **Bullet / Bifrost** workflows documented for your Maya generation, bake
to keys for FBX, or wrap experiments in a **local scene file** you can reopen
after a crash. If you only need motion for export, **keyframed or cached**
results are more stable than live rigid iteration inside one `execute_python`
payload.

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
- `introspect_list_module` — List public names in `maya.cmds` / OpenMaya (paginated)
- `introspect_signature` — Return flag list / method signature for a Maya API name
- `introspect_search` — Case-insensitive search over module names and flag names
- `introspect_eval` — Evaluate a read-only Python expression inside Maya (main-thread)
