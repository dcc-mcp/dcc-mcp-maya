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
    include_bundled: bool = True,
    gateway_port: Optional[int] = None,
    registry_dir: Optional[str] = None,
    dcc_version: Optional[str] = None,
    scene: Optional[str] = None,
    enable_hot_reload: bool = False,
    enable_gateway_failover: bool = True,
    metrics_enabled: Optional[bool] = None,
    job_storage_path: Optional[str] = None,
    job_recovery: Optional[str] = None,
    dcc_pid: Optional[int] = None,
    dcc_window_title: Optional[str] = None,
    dcc_window_handle: Optional[int] = None,
    enable_workflows: Optional[bool] = None,
    host_dispatcher: Optional[Any] = None,
    readiness_timeout_secs: Optional[int] = None,
) -> McpServerHandle
```

启动（或返回已运行的）模块级单例服务器。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port` | `int` | `8765` | TCP 端口。使用 `0` 随机分配可用端口。 |
| `server_name` | `str` | `"maya-mcp"` | MCP `initialize` 响应中显示的名称。 |
| `register_builtins` | `bool` | `True` | 启动时发现内置技能；具体工具集按需加载。 |
| `extra_skill_paths` | `List[str]` | `None` | 额外扫描 `SKILL.md` 文件的目录列表。 |
| `include_bundled` | `bool` | `True` | 发现技能时包含 `dcc-mcp-core` 自带技能。 |
| `gateway_port` | `int \| None` | `None` | 多实例网关选举使用的端口。 |
| `registry_dir` | `str \| None` | `None` | 用于服务发现元数据的共享注册目录。 |
| `dcc_version` | `str \| None` | `None` | 上报到发现注册表中的 Maya 版本。 |
| `scene` | `str \| None` | `None` | 上报到发现注册表中的当前场景路径。 |
| `enable_hot_reload` | `bool` | `False` | 启用 Skill 热重载。 |
| `enable_gateway_failover` | `bool` | `True` | 网关失效时允许非网关实例自动晋升。 |
| `metrics_enabled` | `bool \| None` | `None` | 启用 Prometheus `/metrics`。 |
| `job_storage_path` | `str \| None` | `None` | SQLite job 持久化数据库路径。 |
| `job_recovery` | `str \| None` | `None` | 中断 job 恢复策略：`"drop"` 或 `"requeue"`。 |
| `dcc_pid` | `int \| None` | `None` | 上报给注册表和 gateway 诊断的 PID。 |
| `dcc_window_title` | `str \| None` | `None` | 上报给发现面的窗口标题。 |
| `dcc_window_handle` | `int \| None` | `None` | 上报给发现面的原生窗口句柄。 |
| `enable_workflows` | `bool \| None` | `None` | 启用 core workflow tools。 |
| `host_dispatcher` | `Any \| None` | `None` | core dispatcher bridge 使用的 Maya host dispatcher。 |
| `readiness_timeout_secs` | `int \| None` | `None` | 发布给 readiness 消费方的建议超时时间。 |

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
    include_bundled=False,
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
    gateway_port: Optional[int] = None,
    registry_dir: Optional[str] = None,
    dcc_version: Optional[str] = None,
    scene: Optional[str] = None,
    enable_gateway_failover: bool = True,
    metrics_enabled: Optional[bool] = None,
    job_storage_path: Optional[str] = None,
    job_recovery: Optional[str] = None,
    dcc_pid: Optional[int] = None,
    dcc_window_title: Optional[str] = None,
    dcc_window_handle: Optional[int] = None,
    enable_workflows: Optional[bool] = None,
    host_dispatcher: Optional[Any] = None,
    readiness_timeout_secs: Optional[int] = None,
)
```

### 方法

#### `register_builtin_actions`

```python
server.register_builtin_actions(
    extra_skill_paths: Optional[List[str]] = None,
    include_bundled: bool = True,
) -> MayaMcpServer
```

发现内置 Maya 技能并注册诊断能力。返回 `self` 支持链式调用。

注册过程按阶段执行：core built-ins、recipes tools、skill reference docs、strict skill scan、capability manifest、project tools 和 MCP resources。之后可通过 `load_skill` MCP 工具按需实体化某个技能。

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
| `registry` | `ToolRegistry` | 底层工具（Tool）注册表 |

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
| `DCC_MCP_MAYA_PORT` | `8765` | 直接启动单例服务器时的默认 TCP 端口 |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | 默认服务器名称 |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | Maya 专用技能目录（`;` 分隔）|
| `DCC_MCP_SKILL_PATHS` | — | 全局备用技能目录 |
| `DCC_MCP_MAYA_HOT_RELOAD` | `0` | 设为 `1` 时启用 Skill 热重载 |
| `DCC_MCP_MAYA_METRICS` | `0` | 设为 `1` 时启用 Prometheus `/metrics` |
| `DCC_MCP_MAYA_JOB_STORAGE` | `<data_dir>/jobs.db` | SQLite job 持久化数据库路径 |
| `DCC_MCP_MAYA_JOB_RECOVERY` | `drop` | `requeue` 表示启动后恢复幂等的中断 job |
| `DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER` | `1` | 启用自动网关故障转移选举 |
| `DCC_MCP_MAYA_ENABLE_WORKFLOWS` | `0` | 启用 core workflow tools |
| `DCC_MCP_MAYA_READINESS_TIMEOUT_SECS` | — | readiness 消费方使用的建议超时时间 |
| `DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST` | `0` | 从 `tools/list` 隐藏未加载 skill/group stub |
| `DCC_MCP_MAYA_SIDECAR` | `0` | 从 Maya 插件启动可选 `dcc-mcp-server sidecar` |
| `DCC_MCP_GATEWAY_PORT` | 插件模式下为 `9765` | 网关竞争端口；设为 `0` 可禁用 |
| `DCC_MCP_REGISTRY_DIR` | 操作系统临时目录 | 用于服务发现的共享注册目录 |
