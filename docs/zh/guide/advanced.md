# 高级用法

## 自定义 Skill

创建自己的 Skill 包并将其暴露为 MCP 工具。

### Skill 目录结构

```
my-custom-skill/
├── SKILL.md           ← 必须的清单文件
└── scripts/
    ├── my_action.py   ← 成为工具：my_custom_skill__my_action
    └── another.py
```

### SKILL.md 格式

```yaml
---
name: my-custom-skill
description: "我的自定义 Maya 自动化 Skill"
dcc: maya
version: "1.0.0"
tags: [maya, custom]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# my-custom-skill

描述此 Skill 的功能。
```

### Action 脚本结构

```python
"""模块文档字符串 — 成为 MCP 工具描述。"""

from typing import Any, Dict
import maya.cmds as cmds


def main(
    object_name: str,
    value: float = 1.0,
) -> Dict[str, Any]:
    """Action 文档字符串 — 显示在 MCP tools/list 中。

    Args:
        object_name: 要操作的 Maya 对象。
        value: 带默认值的数值参数。

    Returns:
        包含 'success' 键和可选结果数据的字典。
    """
    result = cmds.getAttr(f"{object_name}.translateY")
    return {
        "success": True,
        "object": object_name,
        "value": result,
    }
```

### 注册自定义 Skill

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(
    port=8765,
    extra_skill_paths=[
        "/path/to/my-skills-folder",
        "/another/skills/directory",
    ]
)
```

或使用环境变量：

```bash
# Windows（分号分隔）
set DCC_MCP_MAYA_SKILL_PATHS=C:\studio\maya-skills;C:\personal\skills

# Linux/macOS（冒号分隔）
export DCC_MCP_MAYA_SKILL_PATHS=/studio/maya-skills:/personal/skills
```

## 主线程调度

Maya 的 UI 和 `cmds` 操作必须在**主线程**运行。插件入口和启动辅助函数都围绕这个约束设计；你自己的自定义代码如果涉及 Maya UI 状态，仍然需要谨慎调度。

如果你的自定义代码需要主线程执行：

```python
import maya.utils

def _my_operation():
    import maya.cmds as cmds
    cmds.polySphere()

# 在主线程下一个空闲时调度
maya.utils.executeDeferred(_my_operation)

# 等待结果（谨慎使用 — 在主线程调用可能死锁）
result = maya.utils.executeInMainThreadWithResult(_my_operation)
```

## 服务器配置

### 自定义端口和名称

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(
    port=9000,
    server_name="maya-studio-2024",
)
print(handle.mcp_url())   # http://127.0.0.1:9000/mcp
```

### 直接使用 MayaMcpServer

```python
from dcc_mcp_maya.server import MayaMcpServer

server = MayaMcpServer(port=8765, server_name="maya-mcp")
server.register_builtin_actions(extra_skill_paths=["/my/custom/skills"])
handle = server.start()

# 停止时：
server.stop()
```

## 日志

启用调试日志进行故障排查：

```python
import logging
logging.getLogger("dcc_mcp_maya").setLevel(logging.DEBUG)
logging.getLogger("dcc_mcp_core").setLevel(logging.DEBUG)
```

## 长任务执行：`defer=True`

`execute_python` 以及任何返回 `DeferredToolResult` 的自定义技能都可以让 MCP 请求线程保持响应，而长任务（烘焙、渲染、模拟、IO）在 Maya 的 idle 队列上运行。

### 何时使用

| 场景 | 推荐 |
|---|---|
| 快速查询 / 属性写入（< 1s） | `defer=False`（默认）— 同步返回 |
| 1–60s，无需 UI | `defer=True` — 客户端轮询直至完成 |
| 多分钟任务（渲染、缓存） | `defer=True` 并提高 `timeout_secs` |
| 必须阻塞请求 | `defer=False`（默认） |

### 在 MCP 客户端中使用（Claude / Cursor / Gemini）

```jsonc
// tools/call 请求
{
  "jsonrpc": "2.0", "id": 7, "method": "tools/call",
  "params": {
    "name": "maya_scripting__execute_python",
    "arguments": {
      "code": "import maya.cmds as cmds\nfor f in range(1, 240):\n    cmds.currentTime(f)\n    cmds.refresh()\n",
      "defer": true,
      "timeout_secs": 600
    }
  }
}
```

服务端立即返回一个延迟句柄；`dcc-mcp-core` 每 100&nbsp;ms 轮询一次该句柄，并在脚本完成（或 `timeout_secs` 到期）时把最终的 `ToolResult` 推送给客户端。

### 取消支持

启用 `defer=True` 的长任务也应配合取消机制：

```python
from dcc_mcp_maya import check_maya_cancelled

for frame in frames:
    check_maya_cancelled()       # 取消时抛出 CancelledError
    cmds.currentTime(frame)
    cmds.render()
```

当 MCP 客户端发出 `notifications/cancelled`（或 dispatcher 触发取消）时，`check_maya_cancelled()` 抛出异常，延迟句柄会以结构化错误信封解析。

### 在自定义技能中返回 `DeferredToolResult`

任何技能都可以通过引入 `dcc-mcp-core` 的辅助类来采用同样的模式：

```python
"""my_long_action.py"""
from typing import Any, Dict


def _runner(state: Dict[str, Any], target: str) -> None:
    import maya.cmds as cmds
    cmds.bakeResults(target, simulation=True, time=(1, 240))
    state["result"] = {"success": True, "message": "Bake complete"}
    state["done"] = True


def main(target: str, defer: bool = True, timeout_secs: float = 600.0):
    if not defer:
        # 同步回退（会阻塞请求线程）。
        state: Dict[str, Any] = {"done": False, "result": None}
        _runner(state, target)
        return state["result"]

    from dcc_mcp_core._server import DeferredToolResult  # 延迟导入

    state = {"done": False, "result": None}

    def _kick() -> None:
        _runner(state, target)

    try:
        import maya.utils
        maya.utils.executeDeferred(_kick)
    except ImportError:
        # mayapy / standalone — 没有 idle 队列；同步执行。
        _kick()

    return DeferredToolResult(
        check_is_finished=lambda: state["result"] if state["done"] else None,
        timeout_secs=float(timeout_secs),
        poll_interval_secs=0.1,
    )
```

在 `tools.yaml` 中声明为 `execution: async`，dispatcher 会为其分配 worker 槽位：

```yaml
- name: my_long_action
  execution: async
  affinity: main
  timeout_hint_secs: 600
  inputSchema:
    type: object
    properties:
      target: { type: string }
      defer: { type: boolean, default: true }
      timeout_secs: { type: integer, default: 600, minimum: 1 }
```

### Dispatcher 如何路由延迟结果

`MayaMcpServer._executor` 通过鸭子类型识别返回值：只要带有 `check_is_finished` 属性，结果就直接透传给 `dcc-mcp-core` 的轮询循环，无需包装、无需复制、无需主线程反射。这意味着延迟启动前抛出的 dispatcher 异常仍会被捕获并以结构化的 `{"success": False, ...}` 信封返回，而轮询完成时则使用技能自身的信封。

### 配置项

| 环境变量 / 参数 | 默认 | 作用 |
|---|---|---|
| `defer=True`（每次调用参数） | `false` | 让本次调用进入延迟路径 |
| `timeout_secs`（每次调用参数） | `3600` | 由 core 轮询循环强制执行的硬超时 |
| `poll_interval_secs`（构造器参数） | `0.1` | core 重新检查 `check_is_finished` 的间隔 |
| `tools.yaml` 中的 `timeout_hint_secs` | — | 透传给 MCP 宿主 UI 的提示值 |

## 生产环境注意事项

### 安全

MCP 服务器默认监听 `127.0.0.1`（本地回环）— **无法从其他机器访问**。如需网络访问，请使用带认证的反向代理。

### 工作室部署

在 `userSetup.py` 中使用条件启动：

```python
# userSetup.py
import os
import maya.utils

def _start_mcp_if_enabled():
    if os.environ.get("DCC_MCP_MAYA_AUTOSTART", "1") == "0":
        return
    import dcc_mcp_maya
    port = int(os.environ.get("DCC_MCP_MAYA_PORT", "8765"))
    handle = dcc_mcp_maya.start_server(port=port)
    print(f"[studio] Maya MCP: {handle.mcp_url()}")

maya.utils.executeDeferred(_start_mcp_if_enabled)
```
