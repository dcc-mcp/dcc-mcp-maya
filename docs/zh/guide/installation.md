# 安装指南

## 系统要求

- **Maya**：2020、2022、2023、2024 或 2025
- **Python**：3.7 – 3.12（Maya 内嵌）
- **dcc-mcp-core**：≥ 0.15.7（作为依赖自动安装）

## 方式一 — pip 安装到 mayapy

最简单的方式，使用 Maya 自身的 Python 解释器：

```bash
# 通用
mayapy -m pip install dcc-mcp-maya

# Windows — Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya

# macOS — Maya 2024
/Applications/Autodesk/maya2024/Maya.app/Contents/bin/mayapy -m pip install dcc-mcp-maya
```

验证安装：

```bash
mayapy -c "import dcc_mcp_maya; print(dcc_mcp_maya.__version__)"
```

## 方式二 — Maya 插件

将插件文件复制到 `MAYA_PLUG_IN_PATH` 中的某个目录，然后通过插件管理器加载。

1. 将 `maya/plugin/dcc_mcp_maya_plugin.py` 复制到 Maya 插件目录，例如：
   - Windows：`%USERPROFILE%\Documents\maya\2024\plug-ins\`
   - macOS：`~/Library/Preferences/Autodesk/maya/2024/plug-ins/`

2. 打开 **窗口 → 设置/首选项 → 插件管理器**

3. 找到 `dcc_mcp_maya`，勾选 **已加载**（可选：勾选**自动加载**）

插件加载后会自动启动服务器。默认情况下实例端口由操作系统分配，并接入 `9765` 端口上的网关。

## 方式三 — mayapy bootstrap

对于 headless E2E 或服务化运行，可以用自带的 bootstrap 启动 Maya：

```bash
mayapy maya_bootstrap.py
```

该 bootstrap 在 batch 模式下创建核心 `BlockingDispatcher`，通过 core host bridge 对外暴露 `/mcp` 和 per-DCC REST skill API `/v1/*`。

Maya 许可证是 CI 中的前置条件。将此命令放到自托管 runner 或有 Maya 许可证的环境中执行。

## 方式四 — userSetup.py（自动启动）

如需每次 Maya 启动时自动开启服务器，在 `userSetup.py` 中添加：

```python
# userSetup.py
import maya.utils

def _start_mcp():
    import dcc_mcp_maya
    handle = dcc_mcp_maya.start_server(port=8765)
    print(f"[dcc-mcp-maya] 服务器已启动：{handle.mcp_url()}")

maya.utils.executeDeferred(_start_mcp)
```

**文件位置：**
- Windows：`%USERPROFILE%\Documents\maya\scripts\userSetup.py`
- macOS：`~/Library/Preferences/Autodesk/maya/scripts/userSetup.py`

## 多 Maya 版本

每个 Maya 版本有独立的 Python 解释器，需分别安装：

```bash
# Maya 2022（Python 3.7）
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Maya 2025
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

同时运行多个 Maya 实例时，使用不同的端口：

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
