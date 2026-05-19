# Multi-Maya-instance Deployment on a Single Workstation

Studios routinely run multiple Maya instances on one workstation — per-shot
sessions for animation, a separate lookdev instance, a background batch
renderer, and so on.  This guide explains how `dcc-mcp-maya` behaves when
N Maya processes share the same machine, and gives a drop-in
`userSetup.py` recipe that keeps every instance discoverable through a
single MCP gateway.

For cross-machine HA deployments, see
[`dcc-mcp-core` production deployment guide](https://github.com/loonghao/dcc-mcp-core)
(core #330) — this page intentionally covers only the single-workstation case.

## Invariants

1. **Every Maya instance must advertise a distinct `dcc_pid`** so the
   `diagnostics__*` tools target the correct process.  The default —
   `os.getpid()` — is almost always what you want; the only time you
   override it is when wrapping Maya with a launcher that proxies the
   real PID.
2. **Every instance reuses the same `FileRegistry` directory.** In
   sidecar mode, the first Maya sidecar that notices the gateway is
   missing starts the standalone machine-wide gateway. All Maya
   processes then register as regular backends. Running two instances
   under *different* `DCC_MCP_REGISTRY_DIR` values makes them
   invisible to each other — only do this intentionally (e.g. per-user
   isolation).
3. **`DCC_MCP_MINIMAL` is per-process.** One instance can run in
   minimal mode (just `maya-scripting` + `maya-scene`) while another
   runs full mode — the gateway reports each backend's active skill
   set independently.
4. **The gateway is independent of any one Maya process.** If a Maya
   process exits, its sidecar exits and the gateway prunes that backend;
   the gateway itself stays up for other Maya, Blender, Photoshop, or
   future DCC sessions on the same workstation.

## Launching N Instances

The bundled `examples/multi-instance/userSetup.py` picks a free port
from a reserved range and registers with `dcc_pid=os.getpid()`.  Drop
it into your Maya `scripts/` directory and every new Maya will
self-register on next launch:

```python
# examples/multi-instance/userSetup.py  (abridged)
from pathlib import Path
import os, socket, logging

PORT_RANGE = range(8765, 8776)      # 11 reserved slots


def _pick_free_port(candidates):
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0                          # OS-assigned fallback


def _apply_multi_instance_env():
    os.environ.setdefault("DCC_MCP_GATEWAY_PORT", "9765")
    os.environ["DCC_MCP_MAYA_PORT"] = str(_pick_free_port(PORT_RANGE))
    os.environ.setdefault("DCC_MCP_MAYA_DCC_PID", str(os.getpid()))
```

The full, commented source is in
[`examples/multi-instance/userSetup.py`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/multi-instance).

## Environment Variable Reference

| Variable | Scope | Default | Purpose |
|---|---|---|---|
| `DCC_MCP_MAYA_PORT` | per-process | `0` (OS-assigned) | HTTP port for this Maya's MCP server |
| `DCC_MCP_GATEWAY_PORT` | per-host | unset (no gateway) | Port the standalone gateway listens on |
| `DCC_MCP_GATEWAY_NAME` | per-host | `dcc-mcp-gateway@<hostname>` | Label shown in admin and CLI gateway diagnostics |
| `DCC_MCP_REGISTRY_DIR` | per-user | platform default | Shared registry every backend writes to |
| `DCC_MCP_MINIMAL` | per-process | `1` | Minimal mode loads only `maya-scripting` + `maya-scene` |
| `DCC_MCP_DEFAULT_TOOLS` | per-process | unset | Comma-separated list overriding minimal skill set |
| `DCC_MCP_MAYA_HOT_RELOAD` | per-process | `0` | Watch bundled skills for edit-on-disk reload |
| `DCC_MCP_MAYA_DCC_PID` | per-process | `os.getpid()` | Value advertised to gateway for `diagnostics__*` routing |

The per-process variables can be set safely **before** Maya launches;
the shared ones must match across every instance on the same user
account, or they'll form separate registry islands.

## Common Topology

```
┌────────────────────────────────────────────────────────────────┐
│  workstation-01                                                │
│                                                                │
│  Maya 2025.0 (anim)     port=8765   dcc_pid=1234   minimal=1  │
│  Maya 2025.1 (lookdev)  port=8766   dcc_pid=5678   minimal=0  │
│  Maya 2025.2 (batch)    port=8767   dcc_pid=9012   minimal=1  │
│                              │                                 │
│                              ▼                                 │
│  shared FileRegistry ──► standalone gateway :9765             │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
                          MCP clients
```

Every backend writes its `(port, pid, dcc_version, skill_list, display_name)`
into the shared registry.  The gateway keeps the routing table current and
exposes a unified discovery surface that flags which backend owns which tool.

## Troubleshooting

### "I see only one instance from the gateway"

Check that all instances read the same `DCC_MCP_REGISTRY_DIR`.  If one
process launched under a different user account it will write into a
different registry root.  Use `dcc_mcp_core.FileRegistry.list()` to
inspect the live entries.

### "My instance never becomes the gateway"

In sidecar mode, Maya instances do not become the gateway. They ensure
the standalone gateway is running, then register as backends. If you
need a separate routing domain, set a unique `DCC_MCP_GATEWAY_PORT`
and matching `DCC_MCP_REGISTRY_DIR` for that launcher.

### "Stale entries after Maya crash"

The gateway's heartbeat prunes dead backends within ~30 s.  To force a
clean slate immediately:

```bash
# Remove the registry directory (recreated on next launch)
python -c "from dcc_mcp_core import get_config_dir; import shutil, os; \
           shutil.rmtree(os.path.join(get_config_dir(), 'registry'), ignore_errors=True)"
```

### "One instance should run full mode, another minimal"

Set `DCC_MCP_MINIMAL` per-launcher, not globally.  A Windows
shortcut for the lookdev session might read:

```
set DCC_MCP_MINIMAL=0
"C:\Program Files\Autodesk\Maya2025\bin\maya.exe"
```

while the animation-pool launcher keeps the default (`=1`).

## Related

- [Advanced Usage](./advanced) — custom skills, main-thread scheduling.
- [`examples/multi-instance/`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/multi-instance) — runnable `userSetup.py`.
- Issue [#88](https://github.com/loonghao/dcc-mcp-maya/issues/88) — this
  document's source of truth for acceptance criteria.
