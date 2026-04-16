# MayaMcpServer API

`MayaMcpServer` 是在 Maya 内嵌入 MCP HTTP 服务器的主要类。

## 类：`MayaMcpServer`

```python
from dcc_mcp_maya.server import MayaMcpServer
```

### 构造函数

```python
MayaMcpServer(
    port: int = 8765,
    server_name: str = "maya-mcp",
    server_version: str = "0.3.0",
    gateway_port: Optional[int] = None,
    registry_dir: Optional[str] = None,
    dcc_version: Optional[str] = None,
    scene: Optional[str] = None,
    enable_gateway_failover: bool = True,
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port` | int | `8765` | TCP 端口，使用 `0` 随机选择可用端口 |
| `server_name` | str | `"maya-mcp"` | MCP `initialize` 响应中显示的名称 |
| `server_version` | str | `"0.3.0"` | MCP `initialize` 响应中显示的版本 |
| `gateway_port` | int \| None | `None` | 多实例发现所用的网关选举端口 |
| `registry_dir` | str \| None | `None` | 发现元数据共享注册目录 |
| `dcc_version` | str \| None | `None` | 上报到注册表的 Maya 版本 |
| `scene` | str \| None | `None` | 上报到注册表的场景路径 |
| `enable_gateway_failover` | bool | `True` | 允许网关故障转移自动晋升 |

### 方法

#### `register_builtin_actions(extra_skill_paths=None, include_bundled=True)`

发现内置 Maya Skill，采用按需加载模式。

```python
server = MayaMcpServer()
server.register_builtin_actions()

# 带自定义路径：
server.register_builtin_actions(extra_skill_paths=["/my/skills"])
```

| 参数 | 类型 | 默认值 | 说明 |
|-----------|------|---------|-------------|
| `extra_skill_paths` | list[str] | `None` | 额外扫描的技能目录 |
| `include_bundled` | bool | `True` | 是否包含 `dcc-mcp-core` 自带技能 |

返回：`self`（支持链式调用）

#### `start()`

启动 MCP HTTP 服务器。

```python
handle = server.start()
print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
```

返回：`McpServerHandle`，包含 `.mcp_url()`、`.port`、`.shutdown()`

#### `stop()`

优雅停止服务器。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_running` | bool | 服务器是否正在运行 |
| `mcp_url` | str \| None | MCP 端点 URL，未运行时为 `None` |

### 示例

```python
from dcc_mcp_maya.server import MayaMcpServer

server = MayaMcpServer(port=8765, server_name="my-maya")
server.register_builtin_actions(extra_skill_paths=["/studio/skills"])
handle = server.start()

print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
print(handle.port)        # 8765

server.stop()
```

## 模块级辅助函数

### `start_server()`

以单例方式启动（或返回已运行的）Maya MCP 服务器。

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

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port` | int | `8765` | TCP 端口 |
| `server_name` | str | `"maya-mcp"` | MCP 服务器名称 |
| `register_builtins` | bool | `True` | 启动时发现内置技能；工具集按需加载 |
| `extra_skill_paths` | list[str] | `None` | 额外技能路径 |
| `include_bundled` | bool | `True` | 是否包含 `dcc-mcp-core` 自带技能 |
| `gateway_port` | int \| None | `None` | 多实例发现的网关选举端口 |
| `registry_dir` | str \| None | `None` | 发现元数据共享注册目录 |
| `dcc_version` | str \| None | `None` | 上报到注册表的 Maya 版本 |
| `scene` | str \| None | `None` | 上报到注册表的场景路径 |
| `enable_hot_reload` | bool | `False` | 是否启用 Skill 热重载 |
| `enable_gateway_failover` | bool | `True` | 是否启用网关故障转移自动晋升 |

### `stop_server()`

停止模块级单例服务器。

```python
dcc_mcp_maya.stop_server()
```

## McpServerHandle

`start()` / `start_server()` 返回的句柄：

| 成员 | 说明 |
|------|------|
| `handle.mcp_url()` | 返回完整的 MCP URL 字符串 |
| `handle.port` | TCP 端口号 |
| `handle.shutdown()` | 停止服务器 |
