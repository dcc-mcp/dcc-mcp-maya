# 安装指南

详细安装说明请参阅英文版 [Installation Guide](/guide/installation)。

## 支持的 Maya 版本

| Maya 版本 | Python | 状态 |
|---|---|---|
| Maya 2026 | 3.11 | ✅ 完全支持 |
| Maya 2025 | 3.11 | ✅ 完全支持 |
| Maya 2024 | 3.10 | ✅ 完全支持 |
| Maya 2023 | 3.9 | ✅ 完全支持 |
| Maya 2022 | 3.7 | ✅ 支持 |
| Maya 2020 | 3.7 | ✅ 支持 |

## 方式一：pip 安装到 mayapy（推荐）

```bash
# Windows
"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" -m pip install dcc-mcp-maya

# macOS
/Applications/Autodesk/maya2026/Maya.app/Contents/bin/mayapy -m pip install dcc-mcp-maya

# Linux
/usr/autodesk/maya2026/bin/mayapy -m pip install dcc-mcp-maya
```

### 验证安装

```bash
mayapy -c "import dcc_mcp_maya; print(dcc_mcp_maya.__version__)"
```

## 方式二：Maya 插件

1. 将 `maya/plugin/dcc_mcp_maya.py` 复制到 `MAYA_PLUG_IN_PATH` 上的目录：
   - Windows：`%USERPROFILE%\Documents\maya\2026\plug-ins\`
   - macOS：`~/Library/Preferences/Autodesk/maya/2026/plug-ins/`
   - Linux：`~/maya/2026/plug-ins/`

2. 在 Maya 中：**窗口 > 设置/首选项 > 插件管理器**

3. 找到 `dcc_mcp_maya` 并勾选**已加载**（可选勾选**自动加载**）

## 方式三：userSetup.py 自动启动

```python
# ~/maya/scripts/userSetup.py
import maya.utils

def _start_mcp_server():
    try:
        import dcc_mcp_maya
        handle = dcc_mcp_maya.start_server(port=8765)
        print(f"[dcc-mcp-maya] 服务器就绪：{handle.mcp_url()}")
    except Exception as e:
        print(f"[dcc-mcp-maya] 启动失败：{e}")

maya.utils.executeDeferred(_start_mcp_server)
```

## 卸载

```bash
mayapy -m pip uninstall dcc-mcp-maya
```
