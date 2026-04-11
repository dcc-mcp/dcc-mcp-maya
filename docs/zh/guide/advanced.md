# 高级用法

## 自定义技能

扩展 `dcc-mcp-maya` 最简便的方式是创建自定义技能 — 包含 `SKILL.md` 描述文件和 Python Action 脚本的目录。

### 技能目录结构

```
my-studio-tools/
├── SKILL.md
└── scripts/
    ├── setup_shot.py
    ├── export_alembic.py
    └── validate_naming.py
```

### SKILL.md 格式

```yaml
---
name: my-studio-tools
description: "Hero Studio 专属流程自动化工具"
dcc: maya
version: "1.0.0"
tags: [maya, pipeline, studio]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# my-studio-tools

## Scripts

- `setup_shot` — 从镜头模板设置新镜头
- `export_alembic` — 将角色缓存导出为 Alembic
- `validate_naming` — 验证对象命名规范
```

### Action 脚本格式

`scripts/` 中的每个脚本成为一个 MCP Action，脚本必须定义与文件名相同的函数：

```python
# scripts/setup_shot.py
"""从工作室模板设置新的 Maya 镜头。"""


def setup_shot(shot_name: str, frame_range: list = None) -> dict:
    """从模板场景设置新镜头并配置。

    Args:
        shot_name: 镜头标识符，如 "SH_0010"
        frame_range: [开始帧, 结束帧]。默认为 [1001, 1100]。

    Returns:
        dict，包含 success (bool)、shot_name (str)、message (str)
    """
    import maya.cmds as cmds

    if frame_range is None:
        frame_range = [1001, 1100]

    template_path = "/pipeline/templates/shot_template.ma"
    cmds.file(template_path, i=True, type="mayaAscii", ignoreVersion=True)

    cmds.playbackOptions(min=frame_range[0], max=frame_range[1])

    if cmds.objExists("SHOT_TEMPLATE"):
        cmds.rename("SHOT_TEMPLATE", shot_name)

    return {
        "success": True,
        "shot_name": shot_name,
        "message": f"镜头 {shot_name} 已设置，帧范围 {frame_range[0]}-{frame_range[1]}",
    }
```

### 注册自定义技能

**方式 A — 环境变量：**
```powershell
# Windows
set DCC_MCP_MAYA_SKILL_PATHS=C:\studio\maya-skills
```

**方式 B — 启动时传入：**
```python
import dcc_mcp_maya
handle = dcc_mcp_maya.start_server(
    extra_skill_paths=["C:/studio/maya-skills"]
)
```

**方式 C — 多路径：**
```powershell
set DCC_MCP_MAYA_SKILL_PATHS=C:\studio\tools;C:\shared\pipeline-skills
```

## MayaMcpServer API

编程控制服务器：

```python
from dcc_mcp_maya.server import MayaMcpServer

server = MayaMcpServer(
    port=9000,
    server_name="my-maya-studio",
)
server.register_builtin_actions(
    extra_skill_paths=["/studio/skills"]
)
handle = server.start()
print(f"运行于 {handle.mcp_url()}")

# 检查状态
if server.is_running:
    print("服务器运行中")

server.stop()
```

## 主线程安全

Maya 的 API **非线程安全** — 所有 `maya.cmds` 和 `OpenMaya` 调用必须在主线程执行。

`dcc-mcp-maya` 自动处理此问题：

1. HTTP 服务器运行在 **Tokio 工作线程**（在 `dcc-mcp-core` 内部）
2. 当 Action 被调用时，通过 `maya.utils.executeDeferred` 分发到 Maya 主线程
3. 通过 `maya.utils.executeDeferred` 安装的轮询回调在每个 UI 帧排空待处理队列

这意味着：
- Action 即使来自多线程 AI 客户端连接也是安全的
- Action 脚本中不需要添加任何线程保护
- 耗时操作会占用主线程直到完成

## 技能发现搜索路径

技能按以下优先级顺序发现（从高到低）：

1. 传给 `start_server()` 或 `register_builtin_actions()` 的 `extra_skill_paths`
2. 本包内置的 `skills/` 目录
3. `DCC_MCP_MAYA_SKILL_PATHS` 环境变量（Maya 专用）
4. `DCC_MCP_SKILL_PATHS` 环境变量（全局备用）
5. 平台默认技能目录（`dcc_mcp_core.get_skills_dir()`）

## 开发时热重载

开发自定义技能时，可启用技能监视器实现热重载（需要 `dcc-mcp-core >= 0.12.10`）：

```python
from dcc_mcp_core import McpHttpServer, ActionRegistry, McpHttpConfig

config = McpHttpConfig(port=8765, server_name="maya-dev")
registry = ActionRegistry()
server = McpHttpServer(registry, config)

server.discover(extra_paths=["/studio/my-skill"], dcc_name="maya")
server.enable_skill_watcher(True)  # 文件变更时热重载
handle = server.start()
```

## 日志调试

启用调试日志以追踪 Action 调用：

```python
import logging
logging.getLogger("dcc_mcp_maya").setLevel(logging.DEBUG)
logging.getLogger("dcc_mcp_core").setLevel(logging.DEBUG)
```

输出到 Maya 的输出窗口/脚本编辑器控制台。

## 插件模式

参阅[安装指南 — 方式二](/zh/guide/installation)了解如何以 Maya 插件方式加载。插件在加载时从环境变量读取 `DCC_MCP_MAYA_PORT`。

加载插件前配置端口：

```python
import os
os.environ["DCC_MCP_MAYA_PORT"] = "9000"

import maya.cmds as cmds
cmds.loadPlugin("dcc_mcp_maya")
```
