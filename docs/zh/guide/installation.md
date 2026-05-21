# 安装指南

## 系统要求

- **Maya**：2020+（模块包覆盖 Maya 2022 至 2026）
- **Python**：3.7 – 3.12（Maya 内嵌）
- **dcc-mcp-core**：≥ 0.17.20（作为依赖自动安装）

## 方式一 — pip 安装到 mayapy

最简单的方式，使用 Maya 自身的 Python 解释器：

```bash
# 通用
mayapy -m pip install "dcc-mcp-maya[sidecar]"

# Windows — Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"

# macOS — Maya 2024
/Applications/Autodesk/maya2024/Maya.app/Contents/bin/mayapy -m pip install "dcc-mcp-maya[sidecar]"
```

验证安装：

```bash
mayapy -c "import dcc_mcp_maya; print(dcc_mcp_maya.__version__)"
```

只有当你的环境已经提供 `dcc-mcp-server` binary 时，才使用不带
`[sidecar]` 的基础包。

## 方式二 — Maya 插件

这是推荐的 Maya GUI 启动方式。将插件文件复制到 `MAYA_PLUG_IN_PATH`
中的某个目录，然后通过插件管理器加载。

1. 将 `maya/plugin/dcc_mcp_maya_plugin.py` 复制到 Maya 插件目录，例如：
   - Windows：`%USERPROFILE%\Documents\maya\2024\plug-ins\`
   - macOS：`~/Library/Preferences/Autodesk/maya/2024/plug-ins/`

2. 打开 **窗口 → 设置/首选项 → 插件管理器**

3. 找到 `dcc_mcp_maya`，勾选 **已加载**（可选：勾选**自动加载**）

插件加载后会自动启动服务器。默认情况下实例端口由操作系统分配，并接入 `9765` 端口上的网关。

默认 sidecar 模式下，本机 MCP 客户端使用 `http://127.0.0.1:9765/mcp`。新版 sidecar binary 还会由选举胜出的 gateway 在局域网暴露 `http://<这台机器的局域网IP>:59765/mcp`。如需关闭局域网入口，可在加载插件前设置 `DCC_MCP_GATEWAY_REMOTE_PORT=0`；如需改绑定地址或端口，设置 `DCC_MCP_GATEWAY_REMOTE_HOST` / `DCC_MCP_GATEWAY_REMOTE_PORT`。

插件初始化期间，`dcc-mcp-maya` 还会关闭 Maya 旧式 MEL commandPort（`127.0.0.1:50007`）。MCP 服务器不会使用该端口，关闭它可以避免误发的 HTTP 探测触发 Maya 安全警告弹窗。如果工作室仍依赖旧式 commandPort，可在加载插件前设置 `DCC_MCP_MAYA_CLOSE_DEFAULT_COMMANDPORT=0` 选择保留。

插件默认会在 Maya 旁边启动 Rust sidecar，同时保留进程内 MCP server 作为 host bridge。如需回到旧的进程内 gateway 路径，请在加载插件前设置 `DCC_MCP_MAYA_SIDECAR=0`。Sidecar 模式使用 Maya 内部 Qt event-loop dispatcher，不需要打开旧式 commandPort。

MCP 宿主配置：

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

## 方式三 — mayapy bootstrap

对于 headless E2E 或服务化运行，可以用自带的 bootstrap 启动 Maya：

```bash
mayapy maya_bootstrap.py
```

该 bootstrap 在 batch 模式下创建 Maya host dispatcher，通过 core host bridge 对外暴露 `/mcp` 和 per-DCC REST skill API `/v1/*`。

Maya 许可证是 CI 中的前置条件。将此命令放到自托管 runner 或有 Maya 许可证的环境中执行。

更多 MCP host 配置、自定义 bootstrap 代码和 standalone-safe custom skill 示例见
[Standalone mayapy 服务](./standalone.md)。

## 方式四 — userSetup.py（自动启动）

如需每次 Maya 启动时自动开启 MCP，推荐复制或 source 仓库自带的
`maya/userSetup.py`。它会设置安全的插件默认值、查找 module 安装，并等
Maya 空闲后再加载插件。

最小自定义 `userSetup.py`：

```python
# userSetup.py
import maya.cmds as cmds
import maya.utils

def _load_dcc_mcp_maya():
    if not cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
        cmds.loadPlugin("dcc_mcp_maya_plugin", quiet=True)

maya.utils.executeDeferred(_load_dcc_mcp_maya, lowestPriority=True)
```

**文件位置：**
- Windows：`%USERPROFILE%\Documents\maya\scripts\userSetup.py`
- macOS：`~/Library/Preferences/Autodesk/maya/scripts/userSetup.py`

避免在 Maya GUI 启动代码里直接调用普通的
`dcc_mcp_maya.start_server(port=8765)`。GUI 会话需要 Maya UI dispatcher
才能执行 `affinity: main` 工具；插件会自动安装它。

## 方式五 — 调试用 direct start_server

直连 server 模式适合本地调试和 `mayapy` 脚本。在 Maya GUI 中请显式传入
dispatcher：

```python
from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump
import dcc_mcp_maya

dispatcher = MayaUiDispatcher()
MayaUiPump(dispatcher).install()
handle = dcc_mcp_maya.start_server(port=8765, host_dispatcher=dispatcher)
print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
```

使用直连模式时，MCP 宿主填写 `http://127.0.0.1:8765/mcp`。插件模式请使用
gateway URL：`http://127.0.0.1:9765/mcp`。

## 多 Maya 版本

每个 Maya 版本有独立的 Python 解释器，需分别安装：

```bash
# Maya 2022（Python 3.7）
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"

# Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"

# Maya 2025
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"
```

同时运行多个 Maya 实例时，插件 gateway 模式更简单：所有实例都会注册到
`http://127.0.0.1:9765/mcp` 后面。

如果你明确要使用直连模式，请为每个实例使用不同端口：

```python
# Maya 2022 实例
handle = dcc_mcp_maya.start_server(port=8762)

# Maya 2024 实例
handle = dcc_mcp_maya.start_server(port=8764)

# Maya 2025 实例
handle = dcc_mcp_maya.start_server(port=8765)
```

在宿主中分别配置：

```json
{
  "mcpServers": {
    "maya-2022": { "url": "http://127.0.0.1:8762/mcp" },
    "maya-2024": { "url": "http://127.0.0.1:8764/mcp" },
    "maya-2025": { "url": "http://127.0.0.1:8765/mcp" }
  }
}
```

## 升级

```bash
mayapy -m pip install --upgrade dcc-mcp-maya
```

## 卸载

```bash
mayapy -m pip uninstall dcc-mcp-maya
```
