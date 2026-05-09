# 单机多 Maya 实例部署

在影视/游戏工作室，工作站上同时运行多个 Maya 实例是常态 —— 动画师
按镜头开多个会话，Lookdev 单独开一个实例，后台再跑一个批量渲染
Maya 等等。本文说明 `dcc-mcp-maya` 在同一台机器跑 N 个 Maya 进程时
的行为，并给出一份可直接使用的 `userSetup.py`，让每个实例都能被单
一的 MCP 网关发现。

跨机器高可用部署见
[`dcc-mcp-core` 生产部署指南](https://github.com/loonghao/dcc-mcp-core)
(core #330)。本文只覆盖单机场景。

## 不变量

1. **每个 Maya 实例必须声明一个独立的 `dcc_pid`**，这样 `diagnostics__*`
   工具才能路由到正确的进程。默认值 `os.getpid()` 在 99% 的情况下都
   是对的；只有当你用 launcher 代理了真实 PID 时才需要覆盖。
2. **所有实例必须共用同一个 `FileRegistry` 目录**。第一个绑定
   `DCC_MCP_GATEWAY_PORT` 的进程赢得网关选举，其余的注册为普通
   backend。把两个实例配置成不同的 `DCC_MCP_REGISTRY_DIR` 会让它们
   互相不可见，除非你是有意为之（例如多用户隔离）。
3. **`DCC_MCP_MINIMAL` 是进程级的**。一个实例可以跑 minimal
   模式（只加载 `maya-scripting` + `maya-scene`），另一个跑 full
   模式 —— 网关会独立报告每个 backend 的 skill 列表。
4. **网关选举是「先到先得」**。被选举的 Maya 崩溃后会在已知 SLA
   内（见 core #303）重新选举，存活的 backend 的工具全程可用。

## 启动 N 个实例

仓库里的 `examples/multi-instance/userSetup.py` 会从一个保留端口段
里挑一个空闲端口，并用 `dcc_pid=os.getpid()` 注册。把它丢到你的
Maya `scripts/` 目录，下次启动的每个 Maya 都会自动注册：

```python
# examples/multi-instance/userSetup.py  （节选）
from pathlib import Path
import os, socket, logging

PORT_RANGE = range(8765, 8776)      # 11 个保留端口


def _pick_free_port(candidates):
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0                          # 让 OS 随机分配


def _apply_multi_instance_env():
    os.environ.setdefault("DCC_MCP_GATEWAY_PORT", "9765")
    os.environ["DCC_MCP_MAYA_PORT"] = str(_pick_free_port(PORT_RANGE))
    os.environ.setdefault("DCC_MCP_MAYA_DCC_PID", str(os.getpid()))
```

完整带注释的源码在
[`examples/multi-instance/userSetup.py`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/multi-instance)。

## 环境变量速查表

| 变量 | 作用域 | 默认值 | 用途 |
|---|---|---|---|
| `DCC_MCP_MAYA_PORT` | 进程级 | `0`（OS 分配） | 当前 Maya MCP 服务器的 HTTP 端口 |
| `DCC_MCP_GATEWAY_PORT` | 主机级 | 未设置（无网关） | 选举出的网关监听的端口 |
| `DCC_MCP_REGISTRY_DIR` | 用户级 | 平台默认 | 所有 backend 共享的注册表目录 |
| `DCC_MCP_MINIMAL` | 进程级 | `1` | minimal mode 只加载 `maya-scripting` + `maya-scene` |
| `DCC_MCP_DEFAULT_TOOLS` | 进程级 | 未设置 | 逗号分隔的 skill 列表，覆盖默认 minimal 集 |
| `DCC_MCP_MAYA_HOT_RELOAD` | 进程级 | `0` | 监听 skill 目录变化并热重载 |
| `DCC_MCP_MAYA_DCC_PID` | 进程级 | `os.getpid()` | 注册到网关的 PID，用于 `diagnostics__*` 路由 |

进程级变量可以在 Maya 启动前放心设置；用户/主机级变量必须在同一
用户下的所有实例间保持一致，否则会形成互相隔离的注册表。

## 典型拓扑

```
┌────────────────────────────────────────────────────────────────┐
│  workstation-01                                                │
│                                                                │
│  Maya 2025.0（动画）    port=8765   dcc_pid=1234   minimal=1  │
│  Maya 2025.1（Lookdev） port=8766   dcc_pid=5678   minimal=0  │
│  Maya 2025.2（批量）    port=8767   dcc_pid=9012   minimal=1  │
│                              │                                 │
│                              ▼                                 │
│  共享 FileRegistry ──► 网关 :9765（由 :8765 选举胜出）        │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
                           MCP 客户端
```

每个 backend 都把自己的 `(port, pid, dcc_version, skill_list)` 写进
共享注册表。网关维护路由表，并对外暴露一个统一的 `tools/list`，清楚
地标注每个工具归属哪个 backend。

## 故障排查

### 「网关只看到一个实例」

检查所有实例读到的 `DCC_MCP_REGISTRY_DIR` 是不是同一个路径。如果
某个进程跑在不同用户下，就会写到不同的注册表根目录去。用
`dcc_mcp_core.FileRegistry.list()` 可以查看当前存活的条目。

### 「我这个实例永远当不上网关」

网关选举是严格的「先绑定先得」。如果另一个 Maya 已经占着
`DCC_MCP_GATEWAY_PORT`，那你这个进程就会以 backend 身份注册 ——
这是设计预期。要强制某个实例当网关，要么让它先启动，要么临时给
它一个独立端口（比如 `DCC_MCP_GATEWAY_PORT=9766`）形成一个独立
路由域。

### 「Maya 崩溃后注册表里有僵尸条目」

网关的心跳大约 30 秒内会清理掉死 backend。要立即清干净：

```bash
# 删除注册表目录（下次启动会自动重建）
python -c "from dcc_mcp_core import get_config_dir; import shutil, os; \
           shutil.rmtree(os.path.join(get_config_dir(), 'registry'), ignore_errors=True)"
```

### 「一个实例跑 full 模式，另一个跑 minimal」

按 launcher 粒度设置 `DCC_MCP_MINIMAL`，不要设成全局变量。
Lookdev 会话的 Windows 快捷方式可以这么写：

```
set DCC_MCP_MINIMAL=0
"C:\Program Files\Autodesk\Maya2025\bin\maya.exe"
```

而动画池的启动器保持默认（`=1`）即可。

## 相关资源

- [高级用法](./advanced) — 自定义 Skill、主线程调度。
- [`examples/multi-instance/`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/multi-instance) — 可运行的 `userSetup.py`。
- Issue [#88](https://github.com/loonghao/dcc-mcp-maya/issues/88) —
  本文的验收标准源头。
