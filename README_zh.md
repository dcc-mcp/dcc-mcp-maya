# DCC-MCP-Maya

<div align="center">

[![PyPI version](https://badge.fury.io/py/dcc-mcp-maya.svg)](https://badge.fury.io/py/dcc-mcp-maya)
[![Build Status](https://github.com/loonghao/dcc-mcp-maya/workflows/Build%20and%20Release/badge.svg)](https://github.com/loonghao/dcc-mcp-maya/actions)
[![Documentation Status](https://readthedocs.org/projects/dcc-mcp-maya/badge/?version=latest)](https://dcc-mcp-maya.readthedocs.io/en/latest/?badge=latest)
[![Python Version](https://img.shields.io/pypi/pyversions/dcc-mcp-maya.svg)](https://pypi.org/project/dcc-mcp-maya/)
[![License](https://img.shields.io/github/license/loonghao/dcc-mcp-maya.svg)](https://github.com/loonghao/dcc-mcp-maya/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/dcc-mcp-maya)](https://pepy.tech/project/dcc-mcp-maya)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/ruff-enabled-brightgreen)](https://github.com/astral-sh/ruff)

</div>

## 简介
模型上下文协议（MCP）的 Maya 集成。此软件包提供通过 RPYC 连接到 Maya 并将 Maya 的功能暴露给 MCP 客户端的功能。

## 特性
- 为 Maya 提供 RPYC 服务器，将 Maya 的功能暴露给外部客户端
- 用于连接到 Maya RPYC 服务器并执行 Maya 命令和脚本的客户端
- 用于将 Maya 与模型上下文协议集成的 MCP 适配器
- 支持远程执行 MEL 脚本和 Maya 命令
- 支持在 Maya 中创建基本对象
- 支持插件扩展
- 与 dcc-mcp-core 集成的插件管理

## 安装
要安装此软件包，请运行以下命令：
```bash
pip install dcc-mcp-maya
```
或者使用 Poetry：
```bash
poetry add dcc-mcp-maya
```

## 使用方法
### 为 MCP 设置 Maya
1. 将 `maya` 目录复制到 Maya 脚本目录或将其添加到 `PYTHONPATH`
2. `userSetup.py` 脚本将在 Maya 启动时自动加载 MCP 插件

### 手动启动 Maya RPYC 服务器
如果插件没有自动加载，您可以在 Maya 脚本编辑器中手动启动它：
```python
from maya_mcp import initialize
initialize()
```
这将在 Maya 中启动一个 RPYC 服务器，将 Maya 的功能暴露给外部客户端。

### 从 Python 连接到 Maya
```python
from dcc_mcp_maya.client import MayaRPyCClient

# 连接到 Maya
client = MayaRPyCClient()

# 执行 MEL 脚本
result = client.execute_mel('sphere -r 5;')

# 执行 Maya 命令
result = client.execute_cmd('polyCube', width=2, height=3, depth=4)

# 获取场景信息
scene_info = client.get_scene_info()
```

### 使用 MCP 适配器
```python
from dcc_mcp_maya.adapter import MayaMCPAdapter

# 创建适配器
adapter = MayaMCPAdapter()

# 在 Maya 中创建基本对象
result = adapter.maya_create_primitive('cube', width=2, height=3, depth=4)

# 执行 Maya 命令
result = adapter.maya_execute_command('polySphere', args='[{"radius": 5}]')

# 执行 MEL 脚本
result = adapter.maya_execute_mel('sphere -r 5;')

# 获取场景信息
scene_info = adapter.maya_get_scene_info()

# 调用插件函数
result = adapter.maya_plugin_call('example_plugin', {'message': 'Hello from MCP!'})
```

### 创建自定义插件
您可以通过创建带有 `func_call` 函数的 Python 模块来为 Maya MCP 创建自定义插件：
```python
# example_plugin.py

# 插件元数据
PLUGIN_INFO = {
    "author": "Your Name",
    "version": "1.0.0",
    "description": "Example plugin for Maya MCP",
    "category": "Example",
}

def func_call(context):
    # 从上下文获取参数
    message = context.get("message", "Hello from Maya MCP plugin!")
    
    # 使用 Maya 做一些事情
    from maya import cmds
    result = cmds.polyCube()
    
    return {
        "status": "success",
        "message": message,
        "result": result,
    }
```
将您的插件放在以下位置之一：
1. 包插件目录：`<package_dir>/plugins/maya/`
2. 用户插件目录：`~/.dcc_mcp/plugins/maya/`
3. 在 `DCC_MCP_PLUGIN_PATHS` 环境变量中指定的自定义路径

## 完整示例
查看 `examples/maya_mcp_example.py` 文件，了解使用 Maya MCP 框架的完整示例。

## 开发
### 环境设置
```bash
# 克隆仓库
git clone https://github.com/loonghao/dcc-mcp-maya.git
cd dcc-mcp-maya

# 安装依赖
pip install -e .[dev]
```

### 创建 Maya 插件包
您可以使用提供的脚本为 Maya 创建可分发的 ZIP 包：
```bash
# 使用 make_maya_zip.py 脚本
python make_maya_zip.py --version 0.1.0 --include-deps

# 或者使用 nox（如果已安装）
nox -s make-maya-zip -- --version 0.1.0 --include-deps
```
这将在 `.zip` 目录中创建一个 ZIP 文件，其中包含安装所需的所有必要文件，包括：
- Maya 插件文件
- userSetup.py 脚本
- 安装批处理文件
- 模块模板文件
- 依赖项（如果指定了 --include-deps）

用户可以通过解压 ZIP 文件并运行包含的 install.bat 文件来安装插件。

### 运行测试
```bash
python -m unittest discover tests
```

## 许可证
MIT
