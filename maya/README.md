# Maya MCP Plugin

这个目录包含了 Maya MCP 插件，用于将 Maya 与 Model Context Protocol (MCP) 集成。

## 目录结构

- `plugin/`: 包含 Maya MCP 插件文件
  - `maya_mcp.py`: 主插件文件，提供 RPYC 服务器功能
  - `README.md`: 插件说明文档
- `userSetup.py`: Maya 启动脚本，用于自动加载插件

## 安装方法

### 开发环境

1. 克隆仓库：
   ```bash
   git clone https://github.com/loonghao/dcc-mcp-maya.git
   cd dcc-mcp-maya
   ```

2. 安装依赖：
   ```bash
   pip install -e .
   ```

3. 将 `maya` 目录链接到 Maya 的脚本目录：
   ```bash
   # Windows
   mklink /D "%USERPROFILE%\Documents\maya\scripts\maya_mcp" "path\to\dcc-mcp-maya\maya"
   
   # Linux/macOS
   ln -s "path/to/dcc-mcp-maya/maya" "$HOME/maya/scripts/maya_mcp"
   ```

### 用户安装

1. 下载最新的发布包
2. 解压缩文件
3. 运行 `install.bat`（Windows）或 `install.sh`（Linux/macOS）

## 打包发布

使用 nox 创建可分发的 ZIP 包：

```bash
# 安装 nox
pip install nox

# 创建 ZIP 包
nox -s make-maya-zip -- --version 0.1.0 --include-deps
```

这将在 `.zip` 目录中创建一个 `maya_mcp-0.1.0.zip` 文件，包含所有必要的文件和依赖项。

## 使用方法

1. 启动 Maya
2. 插件将自动加载并启动 RPYC 服务器
3. 使用 MCP 客户端连接到 Maya

## 配置选项

- `MAYA_MCP_PORT`: 设置 RPYC 服务器的端口号（默认：随机端口）
- `MAYA_MCP_HOST`: 设置 RPYC 服务器的主机名（默认：localhost）
- `MAYA_MCP_DEBUG`: 启用调试日志（设置为 1 启用）

## 依赖项

- `dcc-mcp-rpyc`: RPYC 服务器和客户端功能
- `dcc-mcp-core`: 插件管理和核心功能
