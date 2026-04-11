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
    server_version: str = "0.3.0",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | int | `8765` | TCP port. Use `0` for a random available port. |
| `server_name` | str | `"maya-mcp"` | Name shown in MCP `initialize` response |
| `server_version` | str | `"0.3.0"` | Version shown in MCP `initialize` response |

### Methods

#### `register_builtin_actions(extra_skill_paths=None)`

Discover and load all built-in Maya skills.

```python
server = MayaMcpServer()
server.register_builtin_actions()

# With custom paths:
server.register_builtin_actions(extra_skill_paths=["/my/skills"])
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `extra_skill_paths` | list[str] | `None` | Additional skill directories to scan |

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
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | int | `8765` | TCP port |
| `server_name` | str | `"maya-mcp"` | MCP server name |
| `register_builtins` | bool | `True` | Auto-discover and load built-in skills |
| `extra_skill_paths` | list[str] | `None` | Additional skill paths |

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
