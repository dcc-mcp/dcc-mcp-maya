# 快速开始

5 分钟内让 Maya 与 MCP 宿主建立连接。

## 前置条件

- Maya 2020 或更高版本（Python 3.7+）
- 一个兼容 MCP 的宿主：[Claude Desktop](https://claude.ai/download)、[Cursor](https://cursor.sh/) 或 [OpenClaw](https://github.com/loonghao/openclaw)

## 第一步 — 安装

将包安装到 Maya 的 Python 解释器中：

```bash
mayapy -m pip install "dcc-mcp-maya[sidecar]"
```

Windows 指定 Maya 版本的示例：

```bash
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"
```

只有当你的环境已经提供 `dcc-mcp-server` binary 时，才使用不带
`[sidecar]` 的基础包。

## 第二步 — 加载 Maya 插件

打开 Maya，然后加载 `dcc_mcp_maya_plugin.py`：

1. 打开 **窗口 > 设置/首选项 > 插件管理器**。
2. 找到或浏览到 `maya/plugin/dcc_mcp_maya_plugin.py`。
3. 勾选 **已加载**。
4. 如果希望每次打开 Maya 自动启动 MCP，勾选 **自动加载**。

插件会启动 Maya bridge，启动或加入本机 gateway，并安装 Maya 主线程
工具所需的 Qt dispatcher。

如果不用插件管理器，也可以复制或 source 仓库自带的 `maya/userSetup.py`；
它会等 Maya 空闲后再加载插件。

## 第三步 — 配置 MCP 宿主

### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
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
    "url": "http://127.0.0.1:9765/mcp"
  }
}
```

### 任意 MCP 客户端

插件模式为 MCP 宿主暴露一个 gateway 端点：

```
http://127.0.0.1:9765/mcp
```

## 第四步 — 执行第一个 Action

在 Claude Desktop（或你的 MCP 宿主）中输入：

> **"在 Maya 中创建一个红色球体"**

Agent 应先发现工具、加载需要的 skill（例如 `maya-primitives` 和
`maya-materials`），再调用 typed Maya tools。

或者更具体：

> **"创建一个半径为 2、位置在 (0, 1, 0) 的多边形球体，命名为 'ball'"**

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DCC_MCP_MAYA_PORT` | `8765` | MCP 服务器 TCP 端口 |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | MCP `initialize` 响应中显示的名称 |
| `DCC_MCP_MAYA_SKILL_PATHS` | _(空)_ | 额外 Skill 目录（以冒号/分号分隔） |
| `DCC_MCP_GATEWAY_PORT` | 插件模式为 `9765` | MCP 宿主连接的本机 gateway 端口 |

## 停止服务器

从插件管理器卸载插件即可。若你是手动启动 Python server，则运行
`import dcc_mcp_maya; dcc_mcp_maya.stop_server()`。

## 手动直连服务器

`start_server(port=8765)` 适合调试和 `mayapy` 脚本。在 Maya GUI 中请显式
传入 UI dispatcher，确保 `affinity: main` 工具在 Maya 主线程执行：

```python
from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump
import dcc_mcp_maya

dispatcher = MayaUiDispatcher()
MayaUiPump(dispatcher).install()
handle = dcc_mcp_maya.start_server(port=8765, host_dispatcher=dispatcher)
print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
```

使用手动直连模式时，MCP 宿主配置 `http://127.0.0.1:8765/mcp`，而不是
gateway URL。

## 下一步

- [安装指南](./installation) — 插件模式、userSetup.py、多 Maya 版本配置
- [MCP Tools 指南](./mcp-tools) — 所有可用工具及示例
- [高级用法](./advanced) — 自定义 Skill、主线程调度
