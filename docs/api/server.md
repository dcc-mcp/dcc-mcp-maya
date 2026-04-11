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
) -> McpServerHandle
```

Start (or return the already-running) module-level singleton server.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | `int` | `8765` | TCP port. Use `0` for a random available port. |
| `server_name` | `str` | `"maya-mcp"` | Name shown in MCP `initialize` response. |
| `register_builtins` | `bool` | `True` | Auto-discover and load all built-in skills. |
| `extra_skill_paths` | `List[str]` | `None` | Additional directories to scan for `SKILL.md` files. |

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
    server_version: str = "0.3.0",
    enable_main_thread_executor: bool = True,
)
```

### Methods

#### `register_builtin_actions`

```python
server.register_builtin_actions(
    extra_skill_paths: Optional[List[str]] = None
) -> MayaMcpServer
```

Discover and load all built-in Maya skills. Returns `self` for fluent chaining.

Uses the dcc-mcp-core SkillCatalog API:
1. `server.discover(paths, dcc_name="maya")` — scans for `SKILL.md` files
2. `server.load_skill(name)` — registers each script as an MCP action

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
| `registry` | `ActionRegistry` | The underlying action registry |

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
| `DCC_MCP_MAYA_PORT` | `8765` | Default TCP port (used by plugin mode) |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Default server name |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | Maya-specific skill directories (`;`-separated) |
| `DCC_MCP_SKILL_PATHS` | — | Global fallback skill directories |
