# Maya Introspection Guide

How to chain `dcc_introspect__*` tools to discover, inspect, and call Maya APIs
without guessing from stale training data.

---

## Why introspection matters

`maya.cmds` is a C-extension namespace. `inspect.signature()` raises
`ValueError: no signature found` for every command. Flag names and their
**types change between Maya versions** (e.g., `polyCube` gained `roundLevel`
in 2022, `polyBevel` flag semantics shifted in 2023). Reading the live
signature from the running Maya session is more reliable than any cached doc.

`maya.api.OpenMaya` (`MFn*` classes) _does_ work with `inspect`, but the
meaningful docstrings live in devkit HTML. The bundled
`openmaya_signatures/maya_<version>.json` index ships those docs pre-extracted
so you don't need the devkit at runtime.

---

## Multi-version strategy

We follow the same approach as [pymel's `cmdcache.py`](https://github.com/LumaPictures/pymel/blob/master/pymel/internal/cmdcache.py):

| Source | Used for | Version-specific? |
|--------|----------|-------------------|
| `maya.cmds.help(cmd)` | `maya.cmds` flag list, types, modes | **Yes** — live in running session |
| `openmaya_signatures/maya_<ver>.json` | `OpenMaya` class/method docs | **Yes** — per-file |
| `inspect.getdoc` / `inspect.signature` | `OpenMaya` runtime fallback | Approximately |

**Resolution order** for `dcc_introspect__signature("maya.api.OpenMaya.MFnMesh")`:

1. Load `openmaya_signatures/maya_<current_major_version>.json`
2. If exact version not found, use nearest lower version file.
3. If still not found, fall back to live `inspect.getdoc` + `inspect.signature`.

To regenerate the bundled index for a new Maya version, run inside Maya:

```bash
# From the repo root, with mayapy on PATH:
just regen-openmaya-index
# or directly:
mayapy tools/generate_openmaya_index.py --output src/dcc_mcp_maya/skills/maya-scripting/references/openmaya_signatures/
```

---

## Typical workflow

### 1 — Search for relevant tools or APIs

```python
# Via MCP tool
dcc_introspect__search(module="maya.cmds", query="bevel")
# Returns: ["polyBevel", "polyBevel3", ...]

dcc_introspect__search(module="maya.api.OpenMaya", query="mesh vertex")
# Returns: ["MFnMesh", "MItMeshVertex", "MItMeshPolygon", ...]
```

### 2 — Get exact signature

```python
dcc_introspect__signature("maya.cmds.polyBevel3")
# Returns:
# {
#   "synopsis": "polyBevel3 [flags] [objects]",
#   "flags": [
#     {"short": "o",  "long": "offset",    "type": "float",  "modes": ["create","edit","query"]},
#     {"short": "sg", "long": "segments",  "type": "int",    "modes": ["create","edit","query"]},
#     ...
#   ]
# }

dcc_introspect__signature("maya.api.OpenMaya.MFnMesh.getPoints")
# Returns inspect-based signature + devkit doc from bundled JSON
```

### 3 — Execute directly

```python
# Use execute_python with the correct signature
execute_python("""
import maya.cmds as cmds
result = cmds.polyBevel3("myCube.e[0:3]", offset=0.2, segments=2)
""")
```

---

## `maya.cmds.help()` parser

`dcc_introspect__signature` for `maya.cmds.*` calls `maya.cmds.help(cmd=name)`
internally. The raw output looks like:

```
polyCube  [flags]
Flags:
  -w   -width        Length         (create,edit,query)
  -h   -height       Length         (create,edit,query)
  -d   -depth        Length         (create,edit,query)
  -sx  -subdivisionsX Int           (create,edit,query)
  ...
```

Parsing rules (same as pymel `getCmdInfoBasic`):
- Skip lines without a leading `-`.
- `tokens[0]` = short flag (`-w`), `tokens[1]` = long flag (`-width`).
- `tokens[2:]` = type tokens (`Length`, `Int`, `on|off`, `script`, …).
- `(multi-use)` token → add `"multiuse"` to modes.
- Type mapping: `Length → float`, `Int → int`, `on|off → bool`, `script → callable`, `name → str`.

---

## OpenMaya index schema

Each `openmaya_signatures/maya_<version>.json` has this top-level structure:

```json
{
  "version": "2024",
  "generated_by": "tools/generate_openmaya_index.py",
  "generated_at": "2024-07-01T00:00:00Z",
  "modules": {
    "maya.api.OpenMaya": { ... },
    "maya.api.OpenMayaAnim": { ... },
    "maya.api.OpenMayaRender": { ... },
    "maya.api.OpenMayaUI": { ... }
  }
}
```

Each module entry:

```json
{
  "MFnMesh": {
    "kind": "class",
    "bases": ["MFnDagNode"],
    "doc": "Function set for operations on meshes.",
    "methods": {
      "getPoints": {
        "signature": "(space: int = 4) -> MPointArray",
        "doc": "Returns the positions of all vertices in the specified space.",
        "version_added": null,
        "version_removed": null
      }
    }
  }
}
```

`version_added` / `version_removed` track API churn across Maya releases.

---

## Version-diff awareness

When an agent loads `openmaya_signatures/maya_2025.json` after having previously
used `maya_2024.json`, the `changelog` field lists additions and removals:

```json
{
  "changelog": {
    "2025": {
      "added": ["MFnSubdNames.kInvalidSubdiv", "MFnMesh.getTriangleOffsets"],
      "removed": [],
      "signature_changed": ["MFnNurbsCurve.getPointAtParam"]
    }
  }
}
```

This lets agents note: "I'm on Maya 2025; `getPointAtParam` signature changed —
re-check before calling."
