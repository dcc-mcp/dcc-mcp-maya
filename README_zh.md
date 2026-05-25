# dcc-mcp-maya

Autodesk Maya 的 [DCC Model Context Protocol](https://github.com/loonghao/dcc-mcp-core) (MCP) 生态系统插件。

将符合标准的 **MCP Streamable HTTP 服务器**（2025-03-26 规范）直接嵌入 Maya — 无需外部网关或单独的 IPC 进程。

[![CI](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml/badge.svg)](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/loonghao/dcc-mcp-maya/graph/badge.svg)](https://codecov.io/gh/loonghao/dcc-mcp-maya)
[![PyPI](https://img.shields.io/pypi/v/dcc-mcp-maya)](https://pypi.org/project/dcc-mcp-maya/)
[![Python](https://img.shields.io/pypi/pyversions/dcc-mcp-maya)](https://pypi.org/project/dcc-mcp-maya/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 架构

```
┌─────────────────────────────────────────────────────────┐
│  Maya (embedded Python)                                  │
│                                                          │
│  import dcc_mcp_maya                                    │
│  handle = dcc_mcp_maya.start_server(port=8765)          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  McpHttpServer  (dcc-mcp-core / Rust/axum)      │   │
│  │  POST /mcp  ──►  ToolRegistry                   │   │
│  │  GET  /mcp  ──►  SSE stream                     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────┘
                               │  http://127.0.0.1:8765/mcp
┌─────────────────────────────▼───────────────────────────┐
│  MCP Host  (Claude Desktop / OpenClaw / Cursor / …)      │
└─────────────────────────────────────────────────────────┘
```

## 安装

### 安装到 Maya Python

```bash
mayapy -m pip install dcc-mcp-maya
```

### 作为 Maya 插件

1. 通过 **Window > Settings/Preferences > Plug-in Manager** 加载插件，找到 `dcc_mcp_maya`。
2. 或者添加到 `userSetup.py`：

   ```python
   import maya.cmds as cmds
   cmds.loadPlugin("dcc_mcp_maya_plugin")
   ```

## 快速开始

如果希望 AI agent 帮你安装 Maya 侧依赖、生成 MCP 配置，并引导你在
Maya 插件管理器里启用插件，可以直接对 agent 说：

```text
帮我参考 https://github.com/loonghao/dcc-mcp-maya/blob/main/install.md 去安装
```

Agent 应先阅读
[`install.md`](https://github.com/loonghao/dcc-mcp-maya/blob/main/install.md)，再按
[`skills/dcc-mcp-maya-setup`](https://github.com/loonghao/dcc-mcp-maya/tree/main/skills/dcc-mcp-maya-setup)
中的 setup skill 完成安装、MCP 配置和 smoke prompt 测试。

### 选项 A — 从 Python 脚本面板

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(port=8765)
print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
```

将 MCP 客户端指向上述 URL。

### 选项 B — 加载插件

将 `maya/plugin/dcc_mcp_maya_plugin.py` 复制到 `MAYA_PLUG_IN_PATH` 上的目录。
服务器在插件加载时自动启动。

### 配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `DCC_MCP_MAYA_PORT` | `8765` | MCP 服务器的 TCP 端口 |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | MCP initialize 中显示的名称 |
| `DCC_MCP_MAYA_SKILL_PATHS` | _(无)_ | Maya 专用 skill 搜索根目录（Windows 用分号分隔，Unix 用冒号）；每个根目录可以是单个 skill 包，也可以包含多个子 skill 包 |
| `DCC_MCP_SKILL_PATHS` | _(无)_ | 所有 DCC 适配器的全局回退 skill 搜索根目录 |
| `DCC_MCP_MINIMAL` | `1` | `0` = full mode；`1` = minimal mode |
| `DCC_MCP_DEFAULT_TOOLS` | _(无)_ | 启动时加载的逗号分隔技能名称（覆盖最小默认） |
| `DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON` | `0` | `1`/`true`/`yes`/`on` — 拒绝 `execute_python`（强制技能优先） |
| `DCC_MCP_MAYA_DISABLE_EXECUTE_MEL` | `0` | 同上真值 — 仅拒绝 `execute_mel` |
| `DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT` | `0` | 同上真值 — 同时拒绝 `execute_python` 与 `execute_mel` |

### Studio Skill 路径与 Rez

`DCC_MCP_MAYA_SKILL_PATHS` 会在服务器注册/启动时读取，并按平台路径分隔符切分
（Windows 为 `;`，Linux/macOS 为 `:`）。每一项都是一个 skill 搜索根目录：
它可以直接是单个 skill 包，也可以是多个子 skill 包的父目录：

```text
studio_maya_skills/
└── skills/
    ├── lightbox-maya-dev/
    │   ├── SKILL.md
    │   ├── tools.yaml
    │   └── scripts/
    └── shot-publish/
        ├── SKILL.md
        └── scripts/
```

Rez 包可以在 `package.py` 的 `commands()` 中追加 `skills` 根目录：

```python
def commands():
    env.DCC_MCP_MAYA_SKILL_PATHS.append("{root}/skills")
```

`load_skill("lightbox-maya-dev")`、`search_skills`、gateway `/v1/search` 与
`dcc_capability_manifest` 都基于注册时发现的 skill 集合工作。Maya 启动后如果
Rez context 或环境变量发生变化，需要重启/重载插件或重新启动 server 让适配器重新扫描；
`load_skill` 只会激活已发现的 skill，不会重新扫描新加入的环境路径。

### 渐进式加载（最小模式）

默认情况下，`dcc-mcp-maya` 以**最小工具面**启动 — 仅加载核心技能（`maya-scripting`、`maya-scene`），且只激活基本工具：

| 工具 | 角色 | 来源技能 |
|------|------|-------------|
| `execute_python` | 兜底任意 Python（优先 `load_skill` + 带 schema 的工具） | `maya-scripting`（核心组） |
| `execute_mel` | 兜底任意 MEL | `maya-scripting`（核心组） |
| `get_scene_info` | 读取 | `maya-scene`（核心组） |
| `get_selection` | 读取 | `maya-scene`（核心组） |
| `get_session_info` | 读取 | `maya-scene`（核心组） |
| `search_tools` | 发现 | 核心 |
| `list_skills` | 浏览 | 核心 |
| `load_skill` | 渐进式激活 | 核心 |

所有其他技能显示为 `__skill__<name>` 存根。Agent 调用 `load_skill("maya-primitives")` 按需扩展工具面，并调用 `activate_group("extended")` 在已加载技能中暴露额外的工具组。**推荐策略：**先 `search_skills` / `dcc_capability_manifest` → `load_skill` → 调用带 `inputSchema` 的具体工具；仅在无对应技能或需批量内联时再使用 `execute_python` / `execute_mel`（可用 `DCC_MCP_MAYA_DISABLE_*` 在生产环境禁用）。

**退出**（恢复旧的全加载行为）：

```bash
# 环境变量
export DCC_MCP_MINIMAL=0
```

```python
# 或以编程方式
server = MayaMcpServer(port=8765)
server.register_builtin_actions(minimal=False)
handle = server.start()
```

**通过环境变量自定义默认工具**：

```bash
# 仅在启动时加载特定技能
export DCC_MCP_DEFAULT_TOOLS="maya-scripting,maya-scene,maya-primitives"
```

### 内置技能（零配置）

`dcc-mcp-maya` 自动加载附带在 `dcc-mcp-core` wheel 中的**内置通用技能** — 无需路径配置。

| 技能 | 工具 | 说明 |
|-------|-------|-------|
| `dcc-diagnostics` | `screenshot`, `audit_log`, `action_metrics`, `process_status` | 可观测性与调试 |
| `workflow` | `run_chain` | 多步操作链 |
| `git-automation` | `repo_stats`, `changelog_gen` | Git 分析 |
| `ffmpeg-media` | `convert`, `probe`, `thumbnail` | 需要 `ffmpeg` 在 PATH 中 |
| `imagemagick-tools` | `resize`, `composite` | 需要 `ImageMagick` 在 PATH 中 |

**退出**内置技能：

```python
# 禁用所有内置核心技能
handle = dcc_mcp_maya.start_server(include_bundled=False)

# 或细粒度控制
server = MayaMcpServer()
server.register_builtin_actions(include_bundled=False)
```

**技能搜索路径优先级**（高 → 低）：

1. `extra_skill_paths` 参数
2. 内置 Maya 技能（随此包发布）
3. `DCC_MCP_MAYA_SKILL_PATHS` 环境变量
4. `DCC_MCP_SKILL_PATHS` 环境变量
5. 内置 `dcc-mcp-core` 技能 ← 默认加载
6. 平台默认技能目录

## 可用的 MCP 工具

`dcc-mcp-maya` 附带 **12 个内置技能包**和 **73+ 个 Maya MCP 工具**。
在默认最小模式下，仅核心工具在启动时激活；其余通过 `load_skill` 渐进式加载。

以下章节是代表性类别，而非详尽清单。

### 场景

| 工具 | 说明 |
|------|-------------|
| `get_session_info` | Maya 版本、场景路径、FPS、对象计数 |
| `new_scene` | 创建新场景 |
| `save_scene` | 将场景保存到磁盘 |
| `open_scene` | 打开场景文件 |
| `list_objects` | 列出 DAG 对象（可选类型过滤） |
| `get_selection` | 获取当前选择 |
| `set_selection` | 设置活动选择 |

### 几何体

| 工具 | 说明 |
|------|-------------|
| `create_sphere` | 创建多边形球体 |
| `create_cube` | 创建多边形立方体 |
| `create_cylinder` | 创建多边形圆柱体 |
| `create_plane` | 创建多边形平面 |
| `delete_objects` | 从场景中删除对象 |
| `set_transform` | 设置平移/旋转/缩放 |
| `get_transform` | 查询平移/旋转/缩放 |
| `rename_object` | 重命名对象 |

### 材质

| 工具 | 说明 |
|------|-------------|
| `create_material` | 创建 Lambert/Blinn/Phong/Arnold 材质 |
| `assign_material` | 将材质分配给对象 |
| `set_material_attribute` | 设置材质颜色、粗糙度等 |
| `list_materials` | 列出所有场景材质 |

### 动画

| 工具 | 说明 |
|------|-------------|
| `set_keyframe` | 在对象属性上设置关键帧 |
| `get_keyframes` | 获取对象/属性的关键帧时间 |
| `set_timeline` | 设置播放时间轴范围 |
| `get_current_time` | 获取当前帧编号 |
| `set_current_time` | 设置当前帧编号 |

### 渲染

| 工具 | 说明 |
|------|-------------|
| `set_render_settings` | 设置分辨率、帧范围、渲染器 |
| `capture_viewport` | 将视口捕获为 base64 编码的 PNG |
| `get_scene_render_stats` | 查询面向渲染的场景统计 |

### 几何交换

| 工具 | 说明 |
|------|-------------|
| `import_file` | 导入 FBX/OBJ/Alembic/Maya 文件，并自动加载所需插件 |
| `export_fbx` | 导出场景或选择为 FBX |
| `export_obj` | 导出场景或选择为 OBJ |

### 脚本

| 工具 | 说明 |
|------|-------------|
| `execute_mel` | 执行 MEL 脚本 |
| `execute_python` | 在 Maya 内执行 Python |

## 技能编写（`execution` + `affinity`）

`tools.yaml` 中的每个工具**必须**声明两个字段，以便 MCP 主机知道如何安全地调度它。省略任一个都会破坏异步调度或导致 Maya 在将仅主线程的 Maya API 路由到 Tokio worker 时崩溃：

```yaml
tools:
  - name: playblast
    description: Capture a viewport screenshot as a base64-encoded PNG
    execution: async            # sync | async — 默认 sync
    affinity: main              # main | any  — Maya 工具默认 main
    timeout_hint_secs: 600      # execution: async 时必须设置

  - name: get_render_settings
    execution: sync
    affinity: main              # cmds.getAttr 必须在 UI 线程上运行

  - name: list_export_presets
    execution: sync
    affinity: any               # 纯文件系统读取 — worker 线程安全
    annotations:
      read_only_hint: true
      idempotent_hint: true
```

分类规则（参见 [issue #84](https://github.com/loonghao/dcc-mcp-maya/issues/84)）：

| 字段 | 使用时机 | 说明 |
|-------|-------------|-------|
| `execution: async` | 典型挂钟时间 > 2s（渲染、烘焙、缓存、大型导入/导出、模拟） | 还必须设置 `timeout_hint_secs`。在 MCP 中显示为 `deferredHint=true`。 |
| `execution: sync` | 有界时间查询和单属性设置器 | 默认值。 |
| `affinity: main` | 任何导入 `maya.*`、调用 `OpenMaya` 或使用 `dcc_mcp_maya.api.validate_*` 的内容 | Maya 工具的安全默认值。 |
| `affinity: any` | 纯文件系统 / 纯 Python 工具，从不触碰 Maya | 通过 grep 脚本中的 `import maya` 验证。 |
| `timeout_hint_secs: N` | 与 `execution: async` 一起使用时必需 | 正整数；在 `tools/list` 上变为 `_meta.dcc.timeout_hint_secs`。 |

内置技能注释工作流：

```bash
# 将每技能 / 每工具分类表应用于每个 tools.yaml
python tools/annotate_skill_affinity.py

# CI 检查结果 — 缺少字段或 async-无-timeout 快速失败
python tools/lint_skill_affinity.py
```

lint 在 `Lint Skills` CI 作业中运行，因此添加新工具而没有这些字段的 PR 将被拒绝。

## Claude Desktop 集成

添加到 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

## 要求

- Maya 2020+（Python 3.7+）
- [`dcc-mcp-core`](https://github.com/loonghao/dcc-mcp-core) ≥ 0.17.31

## 技能脚本中的协作取消

长时间运行的技能脚本（渲染、烘焙、动作捕捉摄取等）应在安全的检查点轮询 `check_maya_cancelled()`，以便调度器可以在 MCP 客户端发送 `notifications/cancelled` 时抢占它们：

```python
from dcc_mcp_maya import check_maya_cancelled, maya_success

def render_frames(frames):
    for frame in frames:
        check_maya_cancelled()      # 取消时引发 CancelledError
        cmds.currentTime(frame)
        cmds.render()
    return maya_success("rendered", frames=len(frames))
```

`check_maya_cancelled()` 检查两个取消源：

1. **MCP 请求令牌**（`dcc_mcp_core.cancellation.check_cancelled`）— 当 `tools/call` 的 `notifications/cancelled` 到达时由 HTTP 处理程序设置。
2. **每作业调度器标志** — 由 `MayaUiDispatcher.cancel(...)` 或 `MayaUiDispatcher.shutdown(...)` 设置。覆盖在 MCP 请求外启动的作业（排队批量渲染、scriptJob 等），其中 contextvar 令牌未安装。

在任何这些上下文之外，调用是廉价的无操作，因此即使脚本从交互式 REPL 或单元测试运行，将其放入循环也是安全的。

## 开发

### 克隆和安装

```bash
git clone https://github.com/loonghao/dcc-mcp-maya
cd dcc-mcp-maya
pip install -e ".[dev]"
pytest tests/
```

### Maya 开发设置

#### Unix/macOS

```bash
# 将源代码链接到 Maya 模块目录
just maya-link

# 将 dcc-mcp-core 安装到 Maya Python
just maya-install-core maya-py=/path/to/mayapy
# 或者如果 mayapy 在 PATH 上：
just maya-install-core

# 检查链接状态
just maya-status

# 完整设置
just maya-dev
```

#### Windows (PowerShell)

```powershell
# 将源代码链接到 Maya 模块目录
just maya-link-win

# 将 dcc-mcp-core 安装到 Maya Python
just maya-install-core-win maya-version=2025

# 检查链接状态
just maya-status-win

# 清理（删除符号链接）
just maya-unlink-win
```

**注意**：Windows 符号链接需要以下之一：
- 启用 Windows 开发者模式（Windows 10/11）
- 或以 Administrator 身份运行 PowerShell

如果符号链接失败，脚本将自动回退到复制文件（更改将需要重新运行 `just maya-link-win`）。

### 验证安装

```bash
just verify-deps
```

### 运行测试

```bash
just test-quick
```

## 许可证

MIT — 参见 [LICENSE](LICENSE)。
