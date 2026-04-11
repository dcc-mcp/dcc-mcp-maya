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

Maya 的 UI 和 `cmds` 操作必须在**主线程**运行。`dcc-mcp-maya` 会自动通过 `executeInMainThreadWithResult` 将所有 action 脚本派发到主线程。

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
