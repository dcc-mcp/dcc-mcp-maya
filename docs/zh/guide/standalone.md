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

默认监听：

```text
http://127.0.0.1:8765/mcp
```

MCP host 配置这个 direct URL：

```json
{
  "mcpServers": {
    "maya-standalone": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

常用环境变量：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `DCC_MCP_MAYA_PORT` | `8765` | 当前 `mayapy` 进程的 direct MCP 端口。 |
| `DCC_MCP_GATEWAY_PORT` | bootstrap 中为 `0` | 只有明确要注册到 gateway 时才设为 `9765`。 |
| `DCC_MCP_MAYA_SKILL_PATHS` | 未设置 | 自定义 standalone-safe skill 根目录。 |

仓库里也提供了可运行示例：
[`examples/standalone/run_maya_mcp.py`](https://github.com/loonghao/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)

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
    port=8765,
    gateway_port=None,
    host_dispatcher=dispatcher,
)

print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
threading.Event().wait()
```

`MayaStandaloneDispatcher` 会用一个进程级锁串行执行 Maya 操作。它声明支持
`main` 和 `any` affinity，但 standalone 里没有真正的 UI 主线程可切换；关键
保证是并发 HTTP 请求不会同时进入 `maya.cmds`。

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
[`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report)。

## 现有例子

- [`maya_bootstrap.py`](https://github.com/loonghao/dcc-mcp-maya/blob/main/maya_bootstrap.py) 启动打包好的 standalone
  服务。
- [`examples/standalone/run_maya_mcp.py`](https://github.com/loonghao/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)
  是可复制的服务脚本。
- [`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report)
  展示 headless-safe custom skill。
- `tests/e2e_standalone/` 包含真实 `mayapy` 下的内置工具和 MCP 协议 E2E 覆盖。

## 常见坑

| 现象 | 处理 |
|---|---|
| MCP host 连不上 | 确认 `mayapy` 进程还在，并且 host 指向 `http://127.0.0.1:8765/mcp`。 |
| 工具需要 viewport 或 modelPanel | 使用 GUI 插件模式；headless Maya 没有交互视口。 |
| 找不到自定义 skill | 将 `DCC_MCP_MAYA_SKILL_PATHS` 设为 skill package 的父目录，然后重启 standalone 服务。 |
| 并发调用破坏场景状态 | 所有触碰 Maya 的工具都走 `affinity: main`；`MayaStandaloneDispatcher` 会串行化执行。 |
