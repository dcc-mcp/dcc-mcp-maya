# 贡献自定义技能包

`dcc-mcp-maya` 设计为可扩展的架构。你可以将自己的技能包与内置包并行部署，无需修改核心代码。

## 技能包目录结构

```
my-skill/
├── SKILL.md          ← 必需的 Skill 清单
└── scripts/
    ├── do_something.py
    └── get_info.py
```

`scripts/` 目录下的每个 `.py` 文件都会自动注册为一个 MCP 工具。

## 编写 Action 脚本

每个脚本必须暴露一个**顶层函数，函数名与文件名（去掉 .py）完全一致**：

```python
# scripts/create_locator_grid.py
"""在均匀间隔的位置批量创建定位器网格。"""

from __future__ import annotations
from typing import Optional


def create_locator_grid(
    rows: int = 3,
    cols: int = 3,
    spacing: float = 2.0,
    name_prefix: Optional[str] = "loc",
) -> dict:
    """创建定位器网格。

    Args:
        rows: 行数。
        cols: 列数。
        spacing: 定位器间距（场景单位）。
        name_prefix: 定位器名称前缀。

    Returns:
        包含 ``context.locators`` 列表的 ToolResult dict。
    """
    # 始终在函数内延迟导入 maya.cmds，以允许在 Maya 外部进行技能发现
    import maya.cmds as cmds
    from dcc_mcp_core import success_result, error_result

    try:
        locators = []
        for r in range(rows):
            for c in range(cols):
                loc = cmds.spaceLocator(
                    name=f"{name_prefix}_{r}_{c}",
                    position=(c * spacing, 0, r * spacing),
                )[0]
                locators.append(loc)

        return success_result(
            f"已创建 {len(locators)} 个定位器",
            locators=locators,
            count=len(locators),
        ).to_dict()
    except Exception as exc:
        return error_result("创建定位器网格失败", str(exc)).to_dict()


def main(**kwargs):
    return create_locator_grid(**kwargs)
```

### 关键规则

| 规则 | 原因 |
|------|------|
| 在函数**内部**延迟导入 `maya.cmds` | 技能发现在 Maya 外部进行 |
| 返回 `dict`（使用 `dcc_mcp_core.success_result` / `error_result`）| 统一的 MCP 响应格式 |
| 函数名 = 文件名（无扩展名）| 自动注册依赖此约定 |
| 模块文档字符串 = MCP 工具描述 | 显示给 AI 的工具列表中 |

## 注册技能包

### 方式 1 — 环境变量

将 `DCC_MCP_MAYA_SKILL_PATHS`（或 `DCC_MCP_SKILL_PATHS`）指向技能包的**父目录**：

```
my-skills/
├── my-skill/
│   └── scripts/
└── another-skill/
    └── scripts/
```

```bash
# Windows PowerShell
$env:DCC_MCP_MAYA_SKILL_PATHS = "C:\Users\me\my-skills"
```

```python
# 或在启动 Server 前设置
import os
os.environ["DCC_MCP_MAYA_SKILL_PATHS"] = r"C:\Users\me\my-skills"

import dcc_mcp_maya
dcc_mcp_maya.start_server()
```

### 方式 2 — 直接传入路径

```python
import dcc_mcp_maya

dcc_mcp_maya.start_server(
    extra_skill_paths=[r"C:\Users\me\my-skills"]
)
```

### 方式 3 — 放入内置技能目录

将技能文件夹复制到已安装包的目录下：

```
<site-packages>/dcc_mcp_maya/skills/my-skill/
```

> **注意：** 此方式在包升级时会丢失。推荐开发时使用环境变量，生产部署使用方式 2。

## 命名规则

MCP 工具名称自动推导：

```
{技能目录名.replace("-", "_")}__{脚本文件名（无扩展名）}
```

示例：

| 技能目录 | 脚本文件 | MCP 工具名 |
|----------|----------|------------|
| `my-skill` | `do_something.py` | `my_skill__do_something` |
| `studio-pipeline` | `publish_asset.py` | `studio_pipeline__publish_asset` |

## 本地测试 Action

无需 Maya 即可在 Python shell 中验证脚本结构：

```python
import importlib.util, pathlib

spec = importlib.util.spec_from_file_location(
    "create_locator_grid",
    pathlib.Path("my-skill/scripts/create_locator_grid.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import inspect
print(inspect.signature(mod.create_locator_grid))
```

完整端到端测试请在注册技能包后，通过 AI 主机调用 `dcc_execute_action` MCP 工具。

## 发布前检查清单

- [ ] 模块文档字符串简洁易懂（将显示给 AI）
- [ ] 所有参数都有类型注解和 docstring 描述
- [ ] `maya.cmds` 在函数内延迟导入
- [ ] 成功时返回 `success_result(…).to_dict()`
- [ ] 已知错误时返回 `error_result(…).to_dict()`
- [ ] 存在 `main(**kwargs)` 包装函数
- [ ] 如有文档更新，通过 `vitepress build` 验证
