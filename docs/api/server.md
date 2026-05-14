# MayaMcpServer API

The `MayaMcpServer` class is the main entry point for embedding an MCP server inside Maya.

## Module-Level Functions

### `start_server`

```python
dcc_mcp_maya.start_server(
    port: int = 8765,
    server_name: str = "maya-mcp",
    register_builtins: bool = True,
    extra_skill_paths: Optional[List[str]] = None,
    include_bundled: bool = True,
    gateway_port: Optional[int] = None,
    registry_dir: Optional[str] = None,
    dcc_version: Optional[str] = None,
    scene: Optional[str] = None,
    enable_hot_reload: bool = False,
    enable_gateway_failover: bool = True,
) -> McpServerHandle
```

Start (or return the already-running) module-level singleton server.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | `int` | `8765` | TCP port. Use `0` for a random available port. |
| `server_name` | `str` | `"maya-mcp"` | Name shown in MCP `initialize` response. |
| `register_builtins` | `bool` | `True` | Discover built-in skills during startup; concrete toolsets load on demand. |
| `extra_skill_paths` | `List[str]` | `None` | Additional directories to scan for `SKILL.md` files. |
| `include_bundled` | `bool` | `True` | Include bundled `dcc-mcp-core` skills during discovery. |
| `gateway_port` | `int \| None` | `None` | Port used for multi-instance gateway election. |
| `registry_dir` | `str \| None` | `None` | Shared registry directory for service discovery metadata. |
| `dcc_version` | `str \| None` | `None` | Maya version reported to the discovery registry. |
| `scene` | `str \| None` | `None` | Current scene path reported to the discovery registry. |
| `enable_hot_reload` | `bool` | `False` | Enable skill hot-reload support. |
| `enable_gateway_failover` | `bool` | `True` | Allow non-gateway instances to promote themselves on gateway loss. |
| `metrics_enabled` | `bool \| None` | `None` | Enable Prometheus `/metrics` endpoint. `None` reads `DCC_MCP_MAYA_METRICS=1`. |
| `job_storage_path` | `str \| None` | `None` | SQLite job persistence DB path. `None` reads `DCC_MCP_MAYA_JOB_STORAGE`, else defaults to `<data_dir>/jobs.db`. Set `""` to disable. |
| `job_recovery` | `str \| None` | `None` | Interrupted job recovery: `"drop"` (default) or `"requeue"`. `None` reads `DCC_MCP_MAYA_JOB_RECOVERY`. |

**Returns:** `McpServerHandle` with `.mcp_url()`, `.port`, `.shutdown()`.

**Example:**
```python
import dcc_mcp_maya

# Basic start
handle = dcc_mcp_maya.start_server()
print(handle.mcp_url())  # http://127.0.0.1:8765/mcp

# Custom port + extra skills
handle = dcc_mcp_maya.start_server(
    port=9000,
    extra_skill_paths=["C:/studio/maya-skills"],
    include_bundled=False,
)
```

---

### `stop_server`

```python
dcc_mcp_maya.stop_server() -> None
```

Stop the module-level singleton server.

---

## Class: MayaMcpServer

```python
from dcc_mcp_maya.server import MayaMcpServer
```

### Constructor

```python
MayaMcpServer(
    port: int = 8765,
    server_name: str = "maya-mcp",
    server_version: str = "0.2.29",  # x-release-please-version
    gateway_port: Optional[int] = None,
    registry_dir: Optional[str] = None,
    dcc_version: Optional[str] = None,
    scene: Optional[str] = None,
    enable_gateway_failover: bool = True,
    metrics_enabled: Optional[bool] = None,
    job_storage_path: Optional[str] = None,
    job_recovery: Optional[str] = None,
)
```

### Methods

#### `register_builtin_actions`

```python
server.register_builtin_actions(
    extra_skill_paths: Optional[List[str]] = None,
    include_bundled: bool = True,
) -> MayaMcpServer
```

Discover built-in Maya skills and register diagnostics. Returns `self` for fluent chaining.

Uses the dcc-mcp-core SkillCatalog API:
1. `server.discover(...)` — scans for `SKILL.md` files and indexes skills
2. `load_skill` MCP tooling can then materialize a specific skill on demand

#### `start`

```python
server.start() -> McpServerHandle
```

Start the HTTP server. Returns a `McpServerHandle`.

#### `stop`

```python
server.stop() -> None
```

Gracefully stop the server.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_running` | `bool` | Whether the server is currently running |
| `mcp_url` | `Optional[str]` | The MCP endpoint URL, or `None` if not running |
| `registry` | `ToolRegistry` | The underlying tool registry |

### Example: Full Lifecycle

```python
from dcc_mcp_maya.server import MayaMcpServer

# Create and configure
server = MayaMcpServer(port=8765, server_name="hero-maya")
server.register_builtin_actions(
    extra_skill_paths=["C:/pipeline/maya-actions"]
)

# Start
handle = server.start()
print(f"Server at {handle.mcp_url()}")

# ... Maya session ...

# Stop
server.stop()
```

## McpServerHandle

Returned by `server.start()` and `start_server()`.

| Member | Type | Description |
|--------|------|-------------|
| `.mcp_url()` | `str` | Full MCP endpoint URL |
| `.port` | `int` | Actual bound TCP port |
| `.shutdown()` | — | Stop the server |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DCC_MCP_MAYA_PORT` | `8765` | Default TCP port when you start the singleton server directly |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Default server name |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | Maya-specific skill directories (`;`-separated) |
| `DCC_MCP_SKILL_PATHS` | — | Global fallback skill directories |
| `DCC_MCP_MAYA_HOT_RELOAD` | `0` | Enable skill hot-reload when set to `1` |
| `DCC_MCP_MAYA_METRICS` | `0` | Enable Prometheus `/metrics` endpoint when set to `1` |
| `DCC_MCP_MAYA_JOB_STORAGE` | `<data_dir>/jobs.db` | SQLite job persistence database path |
| `DCC_MCP_MAYA_JOB_RECOVERY` | `drop` | `requeue` to resume idempotent interrupted jobs on startup |
| `DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER` | `1` | Enable automatic gateway failover election |
| `DCC_MCP_GATEWAY_PORT` | `9765` in plugin mode | Gateway competition port; `0` disables gateway mode |
| `DCC_MCP_REGISTRY_DIR` | OS temp dir | Shared registry directory for service discovery |
