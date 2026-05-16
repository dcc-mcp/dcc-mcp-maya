---
name: maya-scripting
description: |-
  Bootstrap stage — escape hatch for Maya work that has no packaged skill yet.
  Agents should prefer search_skills / dcc_capability_manifest → load_skill →
  typed tools (inputSchema + annotations) from domain skills; use execute_python
  or execute_mel only when no skill matches, for bulk in-process loops, or for
  API introspection. Includes introspection tools so an agent can discover flags
  and method signatures without leaving the loop.
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
      last resort after load_skill, no-matching-tool, bulk loop in maya,
      MEL Python escape hatch, inspect api, cmds help, signature,
      flag list, introspect only
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
    skill-reference-docs:
      - "references/*.md"
---
# maya-scripting (Bootstrap stage)

**Skills-first default:** `search_skills` / `dcc_capability_manifest` → `load_skill("<domain>")` → call the concrete tool from `tools.yaml` (validated `inputSchema`, safety hints). Reserve `execute_python` / `execute_mel` for **escape hatches**: no matching skill, intentional bulk work inside one Maya payload, OpenMaya-only gaps, or introspection-only passes.

Studios can hard-block arbitrary execution with `DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON=1`, `DCC_MCP_MAYA_DISABLE_EXECUTE_MEL=1`, or `DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1` (blocks both).

## Decision tree

```
Intent matches a Pipeline-stage skill (shot-export, render-farm, pipeline)?
  → load that skill instead.
Intent matches an Interchange skill (FBX/OBJ/preset import or export)?
  → load maya-geometry / maya-export-preset.
Intent matches an Authoring skill (mesh, uv, material, rig, anim, light)?
  → load that domain skill — its tools.yaml has full inputSchema and safety hints.
Only need cmds / OpenMaya discovery (no mutation)?
  → activate introspect group; prefer introspect_* over execute_python.
Genuine gap, bulk loop, or one-off not worth a new skill yet?
  → load maya-scripting, read RECIPES.md if helpful, call execute_python / execute_mel.
Unsure of flag name or method signature while authoring a script?
  → activate the introspect group, call introspect_signature / introspect_search.
```

## Bulk operations (agent guidance)

When the user wants **many similar steps** inside Maya (e.g. 10 spheres → 10 FBX files with a naming convention, batch import folders, mass rename):

1. **Prefer** loading the owning skill once (`load_skill("maya-geometry")`, `maya-primitives`, …) and either calling typed tools **or** mirroring the same flags after reading that skill's `SKILL.md` contract.
2. When MCP round-trip cost dominates and everything is homogeneous, **one** `execute_python` payload that loops locally and returns structured `context` (`written_files`, `failed`, `roots`) is acceptable — it is still weaker than schema tools for validation and crash isolation.
3. **Do not** emit dozens of sequential tool calls for the same mechanical pattern unless each step must be individually schema-validated or audited.
4. **Gateway clients** (dcc-mcp-gateway): prefer the gateway **REST** API
   (`POST /v1/search`, `/v1/describe`, `/v1/call`, `/v1/call_batch` on the
   gateway port). Use MCP `call_tool` / per-Maya `/mcp` only when your host
   requires Streamable HTTP. Use `call_tools` / `POST /v1/call_batch` for up
   to **25** *distinct* tool steps; for homogeneous bulk I/O, still collapse
   to **one** backend script when possible (see repo `examples/workflows/maya_bulk_rbd_fbx.md`).
5. **Long loops**: import `check_maya_cancelled` from `dcc_mcp_maya` and poll inside the loop so cancellation does not wedge the session.

## Why this skill is special

- It is the **only** stage = `bootstrap` skill. The minimal-mode default
  loads it eagerly so an agent always has a reachable escape hatch.
- Every dispatched job runs inside `dcc_mcp_maya._safe_session.mcp_safe_session`,
  which **snoozes Maya's AutoSave** for the job's duration so an unsaved-scene
  AutoSave prompt cannot block the UI thread mid-dispatch.
- Dialog `cmds.*` entries (`confirmDialog`, `promptDialog`, `fileDialog`,
  `fileDialog2`, `layoutDialog`) are **not** monkey-patched. The previous
  monkey-patch corrupted Maya's internal state on `cmds.file(new=True)`,
  Arnold renderer switch, and other paths where the engine consumes the same
  `cmds.*` entries internally (removed 2026-05-16). If a script genuinely
  needs to spawn a dialog it spawns; rely on the server-side request timeout
  to recover from a hung MCP-dispatched job rather than a global override.

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

- `execute_python` — Inline Python (isolated namespace) or `file_path` / `script_path` to a `.py` (runs in `__main__` with `__file__` / `this_root`, Maya-native)
- `execute_mel` — Inline MEL or `file_path` to a `.mel` (MEL `source` via `mel.eval`)
- `list_mel_procedures` — List available MEL global procedures
- `get_script_node` — Inspect a Maya scriptNode's content
- `introspect_list_module` — List public names in `maya.cmds` / OpenMaya (paginated)
- `introspect_signature` — Return flag list / method signature for a Maya API name
- `introspect_search` — Case-insensitive search over module names and flag names
- `introspect_eval` — Evaluate a read-only Python expression inside Maya (main-thread)
