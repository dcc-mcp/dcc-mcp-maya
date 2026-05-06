# Shutdown Safety Matrix

Issue [#186](https://github.com/loonghao/dcc-mcp-maya/issues/186) hardens the
Maya MCP plugin's shutdown behaviour so non-cooperative Maya exits stop
leaking `FileRegistry` rows. The operator-visible symptom *"Maya 退出后
plugin 服务好像没有退出"* — `list_dcc_instances` continuing to advertise a
just-closed Maya — has two fixes:

1. **Core-side (upstream)** — graceful `handle.shutdown()` deregisters
   from `FileRegistry` on clean exits.
2. **This page (Maya-side)** — four independent safety nets that each
   cover a subset of non-cooperative exit paths, so no single missed
   teardown path leaves a ghost row for long.

## Safety nets

Four nets, landed independently and individually disable-able via env
vars so embedding hosts with their own shutdown orchestration can opt
out of whichever ones they own.

| Net                                   | Env var opt-out                              | Default | What it catches                                                                                              |
|---------------------------------------|----------------------------------------------|---------|--------------------------------------------------------------------------------------------------------------|
| `MSceneMessage.kMayaExiting` hook     | `DCC_MCP_MAYA_KMAYA_EXITING_HOOK=0`          | on      | Clean `File → Exit Maya`, `⌘Q` / Alt+F4 — fires **before** `uninitializePlugin`.                             |
| `atexit` fallback                     | `DCC_MCP_MAYA_ATEXIT_HOOK=0`                 | on      | Plain interpreter teardown (`mayapy` scripts, REPL quit, embedding host that skips `unloadPlugin`).          |
| Crash-resilient process sentinel      | `DCC_MCP_MAYA_PROCESS_SENTINEL=0`            | on      | Hard crashes / `kill -9` / Task Manager End Task — the OS drops the marker file when the process dies.       |
| Defensive `__del__` guard (opt-in)    | `DCC_MCP_MAYA_DEFENSIVE_DEL=1` to enable     | off     | `mayapy` / test-fixture code paths that never call `stop_server()`; disabled by default to avoid Tokio deadlocks during interpreter teardown. |

All four are composed by `ShutdownCoordinator` which the plugin
instantiates once after `_start()` and tears down in
`uninitializePlugin`. The coordinator's guarded-stop wrapper ensures
the callback runs **at most once** even when two nets race (e.g. both
`kMayaExiting` and `atexit` fire on the same exit).

## Exit-path support matrix

| Exit path                              | `uninitializePlugin` | Cleanup guaranteed? | Max stale window | Which net(s) fire                       |
|----------------------------------------|----------------------|---------------------|------------------|-----------------------------------------|
| `File → Exit Maya` (clean)             | Yes                  | **Yes**             | 0 s              | `kMayaExiting` + `uninitializePlugin`   |
| `⌘Q` / Alt+F4 (clean)                  | Maybe                | **Yes**             | 0 s              | `kMayaExiting`                          |
| Plugin unload via `unloadPlugin`       | Yes                  | **Yes**             | 0 s              | `uninitializePlugin`                    |
| `mayapy` script exits normally         | No                   | **Yes**             | 0 s              | `atexit`                                |
| `mayapy` script `os._exit(...)`        | No                   | Partial             | ≤ 30 s           | Process sentinel + gateway sweep        |
| Maya crash                             | No                   | Partial             | ≤ 30 s           | Process sentinel + gateway sweep        |
| `kill -9` / Task Manager End Task      | No                   | Partial             | ≤ 30 s           | Process sentinel + gateway sweep        |
| Ctrl+C in controlling console          | No                   | Partial             | ≤ 30 s           | Process sentinel + gateway sweep        |

"Partial" means: the `FileRegistry` row itself may linger up to
`stale_timeout_secs` (default 30 s), but the adjacent **process
sentinel** is dropped immediately by the OS, so a sweeper / next
gateway cold-start can unambiguously identify the row as dead without
waiting on the heartbeat timeout.

The gateway's periodic sweep runs every 15 s plus a startup sweep, so
the worst-case ghost-row window is bounded at ≈ 45 s for any exit path.

## Env vars (reference)

| Variable                                | Default | Values          | Purpose                                                                                  |
|-----------------------------------------|---------|-----------------|------------------------------------------------------------------------------------------|
| `DCC_MCP_MAYA_KMAYA_EXITING_HOOK`       | `1`     | `0` / `1`       | Disable the `MSceneMessage.kMayaExiting` hook registration.                              |
| `DCC_MCP_MAYA_ATEXIT_HOOK`              | `1`     | `0` / `1`       | Disable the `atexit` fallback.                                                           |
| `DCC_MCP_MAYA_PROCESS_SENTINEL`         | `1`     | `0` / `1`       | Disable the crash-resilient sentinel file (saves one file descriptor per Maya instance). |
| `DCC_MCP_MAYA_DEFENSIVE_DEL`            | `0`     | `0` / `1`       | Opt in to the defensive `__del__` guard. Recommended only for `mayapy` / test fixtures.  |

Values follow the standard truthy/falsy tokens (`0`/`1`, `true`/`false`,
`yes`/`no`, `on`/`off`). Malformed values fall back to the default and
log a debug-level message so a typo never kills plugin load.

## Python API

```python
from dcc_mcp_maya import (
    ShutdownCoordinator,           # composes all four nets
    ProcessSentinel,               # low-level OS marker wrapper
    DefensiveShutdownGuard,        # opt-in __del__ belt
    register_kmaya_exiting_hook,   # helper — registers just the kMayaExiting net
    register_atexit_hook,          # helper — registers just the atexit net
    write_process_sentinel,        # helper — creates just the sentinel
    orphan_sentinels,              # sweeper helper — list sentinels whose PIDs are dead
)
```

Typical integration is already handled by the plugin bootstrap — the
public API is exposed for embedding hosts that want to drive shutdown
themselves (headless orchestrators, custom Maya distributions, test
fixtures).
