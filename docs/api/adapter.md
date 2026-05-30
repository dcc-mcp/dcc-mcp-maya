# MayaMcpServer API

`MayaMcpServer` is the main server class that embeds an MCP HTTP server inside Maya.

## Class: `MayaMcpServer`

```python
from dcc_mcp_maya.server import MayaMcpServer
```

### Constructor

```python
MayaMcpServer(
    port: int = 8765,
    server_name: str = "maya-mcp",
    server_version: str = "0.4.0",  # x-release-please-version
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

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | int | `8765` | TCP port. Use `0` for a random available port. |
| `server_name` | str | `"maya-mcp"` | Name shown in MCP `initialize` response |
| `server_version` | str | `"0.4.0"` | Version shown in MCP `initialize` response | <!-- x-release-please-version -->
| `gateway_port` | int \| None | `None` | Gateway election port for multi-instance discovery |
| `registry_dir` | str \| None | `None` | Shared registry directory for discovery metadata |
| `dcc_version` | str \| None | `None` | Maya version reported to the registry |
| `scene` | str \| None | `None` | Scene path reported to the registry |
| `enable_gateway_failover` | bool | `True` | Allow gateway failover auto-promotion |
| `metrics_enabled` | bool \| None | `None` | Enable Prometheus `/metrics`. `None` reads `DCC_MCP_MAYA_METRICS=1` |
| `job_storage_path` | str \| None | `None` | SQLite job DB path. `None` reads env or defaults to `<data_dir>/jobs.db`. `""` disables |
| `job_recovery` | str \| None | `None` | Interrupted job policy: `"drop"` or `"requeue"`. `None` reads `DCC_MCP_MAYA_JOB_RECOVERY` |

### Methods

#### `register_builtin_actions(extra_skill_paths=None, include_bundled=True)`

Discover built-in Maya skills for progressive loading.

```python
server = MayaMcpServer()
server.register_builtin_actions()

# With custom paths:
server.register_builtin_actions(extra_skill_paths=["/my/skills"])
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `extra_skill_paths` | list[str] | `None` | Additional skill directories to scan |
| `include_bundled` | bool | `True` | Include bundled `dcc-mcp-core` skills |

Returns: `self` (fluent interface)

#### `start()`

Start the MCP HTTP server.

```python
handle = server.start()
print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
```

Returns: `McpServerHandle` with `.mcp_url()`, `.port`, `.shutdown()`

#### `stop()`

Gracefully stop the server.

```python
server.stop()
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_running` | bool | Whether the server is currently running |
| `mcp_url` | str \| None | The MCP endpoint URL, or `None` if not running |

### Example

```python
from dcc_mcp_maya.server import MayaMcpServer

server = MayaMcpServer(port=8765, server_name="my-maya")
server.register_builtin_actions(extra_skill_paths=["/studio/skills"])
handle = server.start()

print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
print(handle.port)        # 8765

# Later:
server.stop()
```

## Module-Level Helpers

### `start_server()`

Start (or return the already-running) Maya MCP server as a singleton.

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(
    port=8765,
    server_name="maya-mcp",
    register_builtins=True,
    extra_skill_paths=None,
    include_bundled=True,
    gateway_port=None,
    registry_dir=None,
    dcc_version=None,
    scene=None,
    enable_hot_reload=False,
    enable_gateway_failover=True,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | int | `8765` | TCP port |
| `server_name` | str | `"maya-mcp"` | MCP server name |
| `register_builtins` | bool | `True` | Discover built-in skills during startup; toolsets load on demand |
| `extra_skill_paths` | list[str] | `None` | Additional skill paths |
| `include_bundled` | bool | `True` | Include bundled `dcc-mcp-core` skills |
| `gateway_port` | int \| None | `None` | Gateway election port for multi-instance discovery |
| `registry_dir` | str \| None | `None` | Shared registry directory for discovery metadata |
| `dcc_version` | str \| None | `None` | Maya version reported to the registry |
| `scene` | str \| None | `None` | Scene path reported to the registry |
| `enable_hot_reload` | bool | `False` | Enable skill hot-reload support |
| `enable_gateway_failover` | bool | `True` | Allow gateway failover auto-promotion |

Returns: `McpServerHandle`

### `stop_server()`

Stop the module-level singleton server.

```python
dcc_mcp_maya.stop_server()
```

## McpServerHandle

The handle returned by `start()` / `start_server()`:

| Member | Description |
|--------|-------------|
| `handle.mcp_url()` | Returns the full MCP URL string |
| `handle.port` | The TCP port number |
| `handle.shutdown()` | Stop the server |
