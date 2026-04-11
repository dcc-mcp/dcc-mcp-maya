# 快速开始

5 分钟内完成 `dcc-mcp-maya` 的安装并连接到 AI 客户端。

## 前提条件

- Maya 2020 或更高版本（Python 3.7+）
- 兼容 MCP 的 AI 客户端：[Claude Desktop](https://claude.ai/download)、[Cursor](https://cursor.com) 或 [OpenClaw](https://github.com/loonghao/openclaw)

## 第一步 — 安装软件包

打开终端，将其安装到 Maya 的 Python 环境：

```bash
# 直接使用 mayapy
mayapy -m pip install dcc-mcp-maya

# 或使用完整路径（Windows 示例）
"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

::: tip Maya 2020–2022
这些版本内置 Python 3.7。包兼容这些版本，但可能需要先升级 pip：
```bash
mayapy -m pip install --upgrade pip
```
:::

## 第二步 — 启动 MCP 服务器

在 Maya 的**脚本编辑器**（Python 标签页）中运行：

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(port=8765)
print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
```

输出示例：
```
http://127.0.0.1:8765/mcp
```

服务器现在已在运行。Maya 继续正常工作 — 服务器运行在后台线程。

### 通过 userSetup.py 自动启动

在每次 Maya 启动时自动开启服务器，将以下内容添加到 `userSetup.py`：

```python
import maya.utils

def _start_mcp():
    import dcc_mcp_maya
    dcc_mcp_maya.start_server(port=8765)

maya.utils.executeDeferred(_start_mcp)
```

## 第三步 — 配置 AI 客户端

### Claude Desktop

编辑配置文件：
- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

重启 Claude Desktop。应能看到 **maya** 列在已连接的 MCP 服务器中。

### Cursor

在 Cursor 设置 → MCP → 添加服务器：

```json
{
  "maya": {
    "url": "http://127.0.0.1:8765/mcp"
  }
}
```

## 第四步 — 执行第一个 Action

在 Claude Desktop 中输入：

> 创建一个名为 "hero_ball" 的红色多边形球体，放置在位置 (0, 5, 0)

Claude 将依次调用：
1. `maya_primitives__create_sphere` 创建球体
2. `maya_materials__create_material` 创建红色 Lambert 材质
3. `maya_materials__assign_material` 将材质指定给球体
4. `maya_primitives__set_transform` 设置位置

球体将实时出现在 Maya 视口中。

## 第五步 — 停止服务器

```python
import dcc_mcp_maya
dcc_mcp_maya.stop_server()
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DCC_MCP_MAYA_PORT` | `8765` | TCP 端口 |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | MCP `initialize` 响应中显示的名称 |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | 额外技能目录（`;` 分隔） |
| `DCC_MCP_SKILL_PATHS` | — | 全局备用技能路径 |

## 常见问题

**端口已被占用：**
```python
handle = dcc_mcp_maya.start_server(port=0)  # 随机可用端口
print(handle.mcp_url())
```

**客户端找不到服务器：**
检查 Maya 脚本编辑器输出，服务器以 `INFO` 级别记录：
```
Maya MCP server started at http://127.0.0.1:8765/mcp
```

## 下一步

- [Action 列表](/zh/guide/actions) — 内置 MCP 工具完整列表
- [MCP Tools 指南](/zh/guide/mcp-tools) — 从 AI 侧如何使用工具
- [高级用法](/zh/guide/advanced) — 自定义技能、插件模式、热重载
