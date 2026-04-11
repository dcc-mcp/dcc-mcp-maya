# MayaMcpServer API（中文）

完整 API 文档参阅英文版 [MayaMcpServer API](/api/server)。

## 模块级函数

### `start_server`

```python
dcc_mcp_maya.start_server(
    port: int = 8765,
    server_name: str = "maya-mcp",
    register_builtins: bool = True,
    extra_skill_paths: Optional[List[str]] = None,
) -> McpServerHandle
```

启动（或返回已运行的）模块级单例服务器。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port` | `int` | `8765` | TCP 端口。使用 `0` 随机分配可用端口。 |
| `server_name` | `str` | `"maya-mcp"` | MCP `initialize` 响应中显示的名称。 |
| `register_builtins` | `bool` | `True` | 自动发现并加载所有内置技能。 |
| `extra_skill_paths` | `List[str]` | `None` | 额外扫描 `SKILL.md` 文件的目录列表。 |

**返回：** `McpServerHandle`，含 `.mcp_url()`、`.port`、`.shutdown()`。

**示例：**
```python
import dcc_mcp_maya

# 基本启动
handle = dcc_mcp_maya.start_server()
print(handle.mcp_url())  # http://127.0.0.1:8765/mcp

# 自定义端口 + 额外技能
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

停止模块级单例服务器。

---

## 类：MayaMcpServer

```python
from dcc_mcp_maya.server import MayaMcpServer
```

### 构造函数

```python
MayaMcpServer(
    port: int = 8765,
    server_name: str = "maya-mcp",
    server_version: str = "0.3.0",
    enable_main_thread_executor: bool = True,
)
```

### 方法

#### `register_builtin_actions`

```python
server.register_builtin_actions(
    extra_skill_paths: Optional[List[str]] = None
) -> MayaMcpServer
```

发现并加载所有内置 Maya 技能。返回 `self` 支持链式调用。

使用 dcc-mcp-core SkillCatalog API：
1. `server.discover(paths, dcc_name="maya")` — 扫描 `SKILL.md` 文件
2. `server.load_skill(name)` — 将每个脚本注册为 MCP Action

#### `start`

```python
server.start() -> McpServerHandle
```

启动 HTTP 服务器，返回 `McpServerHandle`。

#### `stop`

```python
server.stop() -> None
```

优雅地停止服务器。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_running` | `bool` | 服务器是否正在运行 |
| `mcp_url` | `Optional[str]` | MCP 端点 URL，未运行时为 `None` |
| `registry` | `ActionRegistry` | 底层 Action 注册表 |

### 完整生命周期示例

```python
from dcc_mcp_maya.server import MayaMcpServer

server = MayaMcpServer(port=8765, server_name="hero-maya")
server.register_builtin_actions(
    extra_skill_paths=["C:/pipeline/maya-actions"]
)

handle = server.start()
print(f"服务器运行于 {handle.mcp_url()}")

# ... Maya 会话 ...

server.stop()
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DCC_MCP_MAYA_PORT` | `8765` | 默认 TCP 端口（插件模式使用）|
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | 默认服务器名称 |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | Maya 专用技能目录（`;` 分隔）|
| `DCC_MCP_SKILL_PATHS` | — | 全局备用技能目录 |
