# 快速开始

5 分钟内让 Maya 与 MCP 宿主建立连接。

## 前置条件

- Maya 2020 或更高版本（Python 3.7+）
- 一个兼容 MCP 的宿主：[Claude Desktop](https://claude.ai/download)、[Cursor](https://cursor.sh/) 或 [OpenClaw](https://github.com/loonghao/openclaw)

## 第一步 — 安装

将包安装到 Maya 的 Python 解释器中：

```bash
mayapy -m pip install dcc-mcp-maya
```

Windows 指定 Maya 版本的示例：

```bash
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

## 第二步 — 启动服务器

打开 Maya 的**脚本编辑器**（Python 标签页）并执行：

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(port=8765)
print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
```

服务器会立即在后台线程中启动，Maya 保持完全交互状态。

## 第三步 — 配置 MCP 宿主

### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

**文件位置：**
- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`

修改后重启 Claude Desktop。

### Cursor

在 Cursor 设置 → MCP Servers 中添加：

```json
{
  "maya": {
    "url": "http://127.0.0.1:8765/mcp"
  }
}
```

### 任意 MCP 客户端

服务器暴露单一端点：

```
http://127.0.0.1:8765/mcp
```

## 第四步 — 执行第一个 Action

在 Claude Desktop（或你的 MCP 宿主）中输入：

> **"在 Maya 中创建一个红色球体"**

Claude 会自动调用 `maya_primitives__create_sphere` 和 `maya_materials__create_material` 工具。

或者更具体：

> **"创建一个半径为 2、位置在 (0, 1, 0) 的多边形球体，命名为 'ball'"**

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DCC_MCP_MAYA_PORT` | `8765` | MCP 服务器 TCP 端口 |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | MCP `initialize` 响应中显示的名称 |
| `DCC_MCP_MAYA_SKILL_PATHS` | _(空)_ | 额外 Skill 目录（以冒号/分号分隔） |

## 停止服务器

```python
import dcc_mcp_maya
dcc_mcp_maya.stop_server()
```

## 下一步

- [安装指南](./installation) — 插件模式、userSetup.py、多 Maya 版本配置
- [MCP Tools 指南](./mcp-tools) — 所有可用工具及示例
- [高级用法](./advanced) — 自定义 Skill、主线程调度
