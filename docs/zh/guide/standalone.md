# Standalone mayapy 服务

当你希望 Maya 以 headless 服务运行时使用 standalone 模式：CI、渲染农场
辅助、批量资产处理，或一个由 MCP host 控制的长驻 `mayapy` 进程。

GUI 插件模式仍然是艺术家工作站的常规路径。Standalone 模式不同：没有 Qt
UI event loop，没有 model panel，也没有插件 sidecar banner。你需要启动
`mayapy`，初始化 `maya.standalone`，然后直接暴露 MCP。

## 启动 Standalone MCP Server

最短路径是仓库自带 bootstrap：

```bash
mayapy maya_bootstrap.py
```

默认由操作系统分配空闲实例端口。复制 bootstrap 输出的地址（或运行
`dcc-mcp-cli list`），例如：

```text
http://127.0.0.1:<assigned-port>/mcp
```

MCP host 配置这个 direct URL：

```json
{
  "mcpServers": {
    "maya-standalone": {
      "url": "http://127.0.0.1:<assigned-port>/mcp"
    }
  }
}
```

常用环境变量：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `DCC_MCP_MAYA_PORT` | 操作系统分配 | 当前 `mayapy` 进程可选的固定 direct MCP 端口。 |
| `DCC_MCP_GATEWAY_PORT` | bootstrap 中为 `0` | 只有明确要注册到 gateway 时才设为 `9765`。 |
| `DCC_MCP_MAYA_SKILL_PATHS` | 未设置 | 自定义 standalone-safe skill 根目录。 |

仓库里也提供了可运行示例：
[`examples/standalone/run_maya_mcp.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)

```bash
mayapy examples/standalone/run_maya_mcp.py
```

## 自定义 Bootstrap

如果你需要完全控制启动逻辑，初始化 Maya 后挂上 standalone dispatcher：

```python
import threading
import maya.standalone

from dcc_mcp_maya import start_server, stop_server
from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

maya.standalone.initialize(name="python")

dispatcher = MayaStandaloneDispatcher()
handle = start_server(
    gateway_port=None,
    host_dispatcher=dispatcher,
)

print(handle.mcp_url())  # 操作系统分配的实例直连地址
stop = threading.Event()
try:
    while not stop.wait(0.01):
        dispatcher.drain_queue(budget_ms=8)
finally:
    stop_server()
    maya.standalone.uninitialize()
```

`MayaStandaloneDispatcher` 将场景操作排队交给初始化 Maya 的主线程。
HTTP 客户端在其他线程或进程运行时，主线程必须调用 `drain_queue()`。
仅用 `Event.wait()` 阻塞主线程无法处理场景请求。首次 pump 前 readiness
保持未就绪；关闭 dispatcher 会中断排队请求。`affinity: any` 仅用于纯 Python
或文件系统操作。

长驻服务优先使用 `serve_headless()`，`mayapy -m dcc_mcp_maya` 和仓库示例
都使用它。它通过 Core dispatcher 统一管理主线程 pump、服务生命周期和清理。

## Windows 上的优雅关闭

本节适用于 **Windows standalone** 服务模式（`serve_headless()` 与
`mayapy -m dcc_mcp_maya`）。结论已在 **Windows + Maya 2022、2024、2026** 上验证，
不代表其他平台或未来 Maya 版本。

该模式唯一经过验证的优雅关闭路径，是你传给 `serve_headless(stop_event=...)`
的程序化停止事件。所有权划分与启动时一致：你负责 Maya 初始化和停止事件，
`serve_headless()` 负责它自己的 server、dispatcher 以及 owning-main-thread pump。
设置该 event 后 pump 循环会返回，随后 `serve_headless()` 执行其 `finally` 块
（`server.stop()` 与 `host.stop()`）。进程随后以退出码 0 退出、端口释放，
实例会从 `services.json` 和 `locks/` 中移除。

请从你自己的线程或管理程序触发停止——例如 watchdog、任务完成回调或空闲计时器——
而不是依赖控制台信号（见下文）。

```python
import threading

import maya.standalone

from dcc_mcp_maya import serve_headless

maya.standalone.initialize(name="python")

stop_event = threading.Event()
try:
    # 阻塞当前（主）线程并泵送 Core dispatcher，直到 event 被设置。
    # 从其他线程设置它即可结束循环并运行清理：
    #
    #     stop_event.set()
    #
    serve_headless(stop_event=stop_event)
finally:
    maya.standalone.uninitialize()
```

完整的起步示例见
[`examples/standalone/run_maya_mcp.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)。

### Windows 上不支持控制台信号

在受测的 Windows standalone 版本中，交互式控制台快捷键无法产生干净的关闭：

- **Ctrl+C（`CTRL_C_EVENT`）** 被忽略——主线程阻塞在 Maya 的 native dispatcher
  中，Python 的 `SIGINT` handler 不会执行，也不会抛出 `KeyboardInterrupt`。
- **Ctrl+Break（`CTRL_BREAK_EVENT`）** 通过 Maya 的 Intel Fortran 运行时
  （`forrtl: error (200)`）终止进程，而不是抛出 Python `KeyboardInterrupt`，
  因此入口处的 `try`/`except KeyboardInterrupt` 与 `finally` 清理都不会执行。

由于 `python -m dcc_mcp_maya` 会一直服务到被中断，在 Windows 上不要依赖控制台
信号来停止它，而应使用该停止事件驱动生命周期。

### 关闭方式对比

| 关闭方式 | 干净退出 | 端口释放 | 注册表（`services.json` / `locks/`） |
|---|---|---|---|
| `stop_event.set()`（程序化） | 是 — rc 0 | 是 | 清空 |
| Ctrl+C（`CTRL_C_EVENT`） | 否 — 被忽略；服务继续运行 | 不适用 | 不变 |
| Ctrl+Break（`CTRL_BREAK_EVENT`） | 否 — 被 Maya 运行时杀死 | 是 | 可能残留死 pid 记录和孤儿 `.lock` 文件 |
| 强制终止（`taskkill /F`） | 否 — 被杀死 | 是 | 可能残留死 pid 记录和孤儿 `.lock` 文件 |

强制终止 standalone 服务是一个已知限制：它可能残留过期的 `services.json` 记录和
孤儿锁文件。这些残留是非破坏性的——不会触及场景数据——且可恢复：Core 会在下次读取
注册表时自动清除死 pid 记录，而通过停止事件路径关闭的服务不会留下任何残留。对于需要
干净停止的服务，请优先使用程序化停止路径，并把强制终止当作最后手段而不是常规做法；
不要将手动清理注册表或锁文件纳入常规操作。

## 编写 Standalone-Safe Skills

遵守常规规则时，大多数 typed Maya skills 可以不改就跑在 `mayapy` 中：

- 在 tool 函数内部 lazy-import `maya.cmds`。
- 任何触碰 Maya scene state 的工具都声明 `affinity: main`。
- 避免 UI-only 命令，例如 model panel、viewport capture、file dialog、
  prompt dialog 和依赖交互选择的流程。
- 长循环里调用 `check_maya_cancelled()`。
- 只有纯 Python 或纯文件系统逻辑才用 `affinity: any`，且不能 import
  `maya.*`。

最小 skill 脚本：

```python
from dcc_mcp_core.skill import skill_entry
from dcc_mcp_maya.api import maya_success, maya_from_exception


def create_batch_cube(name: str = "batch_cube") -> dict:
    try:
        import maya.cmds as cmds

        result = cmds.polyCube(name=name)
        return maya_success("Created cube", object_name=result[0])
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create cube")


@skill_entry
def main(**kwargs) -> dict:
    return create_batch_cube(**kwargs)
```

对应 `tools.yaml`：

```yaml
tools:
  - name: create_batch_cube
    description: Create a cube in mayapy / Maya standalone.
    execution: sync
    affinity: main
    inputSchema:
      type: object
      properties:
        name:
          type: string
          default: batch_cube
```

加载自定义 skills 时，让 `DCC_MCP_MAYA_SKILL_PATHS` 指向包含 skill package
的父目录：

```bash
# Windows PowerShell
$env:DCC_MCP_MAYA_SKILL_PATHS = "$PWD\examples\standalone\custom-skills"
mayapy examples/standalone/run_maya_mcp.py
```

完整示例 skill 在
[`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/dcc-mcp/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report)。

## 现有例子

- [`maya_bootstrap.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/maya_bootstrap.py) 启动打包好的 standalone
  服务。
- [`examples/standalone/run_maya_mcp.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)
  是可复制的服务脚本。
- [`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/dcc-mcp/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report)
  展示 headless-safe custom skill。
- `tests/e2e_standalone/` 包含真实 `mayapy` 下的内置工具和 MCP 协议 E2E 覆盖。

## 常见坑

| 现象 | 处理 |
|---|---|
| MCP host 连不上 | 确认 `mayapy` 进程还在，并运行 `dcc-mcp-cli list` 刷新实例直连地址。 |
| 工具需要 viewport 或 modelPanel | 使用 GUI 插件模式；headless Maya 没有交互视口。 |
| 找不到自定义 skill | 将 `DCC_MCP_MAYA_SKILL_PATHS` 设为 skill package 的父目录，然后重启 standalone 服务。 |
| 并发调用破坏场景状态 | 所有触碰 Maya 的工具都走 `affinity: main`；`MayaStandaloneDispatcher` 会串行化执行。 |
