# Introduction

**dcc-mcp-maya** is the Maya-specific integration layer for the [DCC-MCP](https://github.com/loonghao/dcc-mcp-core) ecosystem.

It makes Maya available through a standards-compliant **MCP Streamable HTTP** surface. Plugin deployments use the Rust `dcc-mcp-server` sidecar as the standard runtime: HTTP and gateway work stay outside Maya, while scene operations are dispatched back through the Maya-safe Qt bridge.

## Who Is This For?

| Audience | Use Case |
|----------|----------|
| **Maya TD / TA** | Write custom Action scripts that AI agents can call via MCP |
| **AI Application Developers** | Control Maya programmatically through MCP protocol from LLM hosts |
| **DCC Integration Developers** | Use this Maya implementation as a reference for other DCC integrations |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Maya (embedded Python)                                  │
│                                                          │
│  dcc_mcp_maya_plugin.py                                 │
│  Qt dispatcher + sidecar bridge                         │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  DccServerBase + McpHttpServer                  │   │
│  │  POST /mcp  ──►  ToolRegistry / tools/call      │   │
│  │  GET  /mcp  ──►  SSE stream                     │   │
│  │  /v1/*       ─►  readiness, search, resources   │   │
│  └──────────────────────┬──────────────────────────┘   │
│                         │ HostExecutionBridge          │
│  ┌──────────────────────▼──────────────────────────┐   │
│  │  MayaHost / dispatcher / skill executor         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────┘
                               │  http://127.0.0.1:9765/mcp
┌─────────────────────────────▼───────────────────────────┐
│  MCP Host  (Claude Desktop / OpenClaw / Cursor / …)      │
└─────────────────────────────────────────────────────────┘
```

## Key Concepts

### Skills

Skills are directory-based packages containing Python action scripts and a `SKILL.md` manifest. Each script becomes an MCP tool automatically.

```
maya-scene/
├── SKILL.md          ← metadata: name, description, tags
└── scripts/
    ├── new_scene.py
    ├── save_scene.py
    └── list_objects.py
```

### Action Naming

Actions follow the convention:

```
{skill_name.replace("-", "_")}__{script_stem}
# e.g.  maya_scene__new_scene
#       maya_primitives__create_sphere
```

### Progressive Loading

The package ships 24 Maya skill packages. Minimal mode loads only the core
bootstrap and scene tools, while unloaded skills remain discoverable through
`dcc_capability_manifest`, `search_skills`, or `search_tools`.

Load a domain skill only when the task needs it:

```python
load_skill("maya-primitives")
```

### Skill Search Path

Paths are resolved in order (highest priority first):

1. `extra_skill_paths` argument
2. Built-in skills shipped with this package
3. `DCC_MCP_MAYA_SKILL_PATHS` environment variable
4. `DCC_MCP_SKILL_PATHS` environment variable
5. Platform default skills directory

Each environment entry is a skill search root: either the skill package itself
or a parent directory whose immediate children are skill packages. Rez packages
typically append `{root}/skills` from `package.py`, then Maya must restart or
rerun registration for a changed environment to affect gateway search and
`load_skill`.

## Next Steps

- [Quick Start](./getting-started) — get Maya talking to Claude Desktop in 5 minutes
- [Local MCP + debug](./local-mcp-debug) — Cursor MCP URL, debugpy attach, gateway vs direct port
- [MCP Tools Guide](./mcp-tools) — user-facing examples and skill routing guidance
- [Advanced Usage](./advanced) — custom skills, main-thread scheduling, `defer=True` long-running scripts
- [Multi-instance Deployment](./multi-instance) — run multiple Maya instances on a single workstation
- [Strict Skill-Only Regression](./strict-skill-only-regression) — automated performance regression suite (PIP-481) that validates strict skill-only workflows
