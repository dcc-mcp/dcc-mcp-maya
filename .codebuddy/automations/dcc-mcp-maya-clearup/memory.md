# dcc-mcp-maya 清理 Agent 执行历史

## 2026-04-10（第一轮）

### 基线状态
- 分支：`feat/skills-sop`（已提前于 origin/main 26 个提交）
- 测试：1003 个测试全部通过（排除 e2e）
- ruff check：通过（无 lint 问题）

### 已完成清理

**阶段 1 - 过期代码清理（server.py）**
- 删除了 `self._poll_job = None`（未使用属性，设置后从未读取）
- 更新了 `list_skills()` 兼容注释：明确当前版本返回 dict（非 SkillSummary 对象）

**已核查无问题的项目**
- Python 3.9+ 泛型语法（`list[str]`）：所有 skills 脚本都有 `from __future__ import annotations`，无裸用
- 海象运算符 `:=` / `match/case`：不存在
- `get_app_skill_paths_from_env`：虽不在 `llms-full.txt` 中，但实际已存在于 `dcc_mcp_core` 中，保留
- `_executor.poll_pending()`：executor 永远是 None，但测试专门通过注入 `fake_executor` 覆盖此路径，保留
- tests/test_skills_round2~round14：各覆盖不同 skill 域，不是重复文件

### 质量门禁
- ruff check src/ tests/：✅ All checks passed
- pytest 1003 tests：✅ All passed (1.45s)

---

## 2026-04-10（第二轮）

### 清理内容

**阶段 1 - 死代码清理（server.py）**
- 删除 `enable_main_thread_executor` 构造参数（一直是 no-op placeholder）
- 删除 `_executor` / `_enable_executor` 属性
- 删除 `_setup_executor()` 方法（只打一条 debug log，executor 永远为 None）
- 删除 `_setup_poll_callback()` 方法（内部 `if self._executor is not None` 永远为 False）
- 更新 `start()` 方法（移除 `_setup_poll_callback()` 调用）
- 更新类 docstring（移除 `enable_main_thread_executor` 参数说明）

**阶段 2 - 测试文件清理**
- `test_server_extended.py`：删除 `TestExecutorSetup` 和 `TestPollCallback` 两个测试类（6 个测试）
- `test_server_coverage.py`：删除 `TestRepeatingPollClosure` 测试类（3 个测试），更新文件头注释
- 批量移除 4 个测试文件中所有 `enable_main_thread_executor=False/True` 参数

**保留的兼容代码（有据可查）**
- `list_skills()` 返回值兼容层（`hasattr(summary, "name") else summary["name"]`）：实测当前安装版本确实返回 dict，llms-full.txt 描述的是目标版本行为，**不可删除**

### 质量门禁
- ruff check src/ tests/：✅ All checks passed
- pytest 1230 tests：✅ All passed (1.65s)（测试数量从 1003 增加是因为上一轮后新增了更多 skills 测试）

---

## 2026-04-10（第四轮）

### 背景
auto-improve worktree 路径为 `G:\PycharmProjects\github\dcc-mcp-maya-auto-improve`（非 .maya-cleanup）。
rebase 失败（33 个提交冲突），改用 merge（Already up to date，无需合并）。

### 测试基线状态（修复前）
- 919 failed, 985 passed, 1 skipped（大量 test_actions_*.py 引用已删除的 dcc_mcp_maya.actions 模块）
- ruff check：61 errors（41 可自动修复）

### 根因
editable install 指向主 workspace（feat/skills-sop）：
- 主 workspace 已删除 `dcc_mcp_maya.actions` 模块 → test_actions_*.py 全部失败（ModuleNotFoundError）
- 主 workspace 已删除 `enable_main_thread_executor` 参数 → server 测试 TypeError

### 清理内容

**阶段 2 - 测试文件清理**
- 删除 17 个 `test_actions_*.py`（测试目标 dcc_mcp_maya.actions 已在 round3 删除）
- 删除 `TestExecutorSetup`、`TestPollCallback` 两个测试类（测试已删除的 executor/poll-callback）
- 修复 test_server.py / test_server_extended.py / test_server_coverage.py：移除所有 `enable_main_thread_executor` 过期参数（共 8 处）

**阶段 1 - 死代码清理（skills 脚本）**
- `mesh_ops.py:332`：删除 `length_info = cmds.polyInfo(...)` 赋值（结果从未使用）
- `uv_ops.py:48`：删除 `v_coords = cmds.polyEditUV(...)` 赋值（结果从未使用）

**阶段 3 - ruff 规范治理**
- `ruff format`：25 个文件重新格式化
- `ruff check --fix`：14 个问题自动修复（unused imports: Dict/Optional/List，import ordering）

### 质量门禁
- ruff check src/ tests/：✅ All checks passed
- pytest 995 tests：✅ All passed, 1 skipped (1.37s)（基线从 1397 降到 995，因删除 17 个 test_actions_*.py）
- 推送：`f7ae60a..d29a0b8 auto-improve -> auto-improve` ✅

### 下一轮关注点
- `list_skills()` 兼容层 `hasattr(summary, "name") else summary["name"]`：等待 dcc_mcp_core 实际返回 SkillSummary 后可简化
- `_setup_executor()` 和 `_setup_poll_callback()` 占位符方法（auto-improve 分支 server.py 仍存在，主 workspace 已删除）：下次同步时可删除
- auto-improve 分支的 server.py 仍保留 enable_main_thread_executor 参数，与主 workspace 不一致；下一轮可同步删除

### 背景
auto-improve 分支与 origin/main 有大量冲突（origin/main 完成了 skills-sop 架构迁移，删除了旧 actions 目录），需要先解决合并冲突再执行清理。

### 合并冲突解决
- `.gitignore`：接受 origin/main 版本（theirs）
- `src/dcc_mcp_maya/actions/__init__.py`, `primitives.py`, `scene.py`：接受 origin/main 删除（theirs）
- `src/dcc_mcp_maya/skills/maya-scripting/scripts/`（25 个文件）：保留 auto-improve 新增内容（ours）
- `tests/test_server_extended.py`：接受 origin/main 的 no-op executor 版本（theirs）
- 提交：`17efc1e chore(merge): resolve conflicts with origin/main`

### 清理内容

**阶段 1 - server.py 残余死代码（origin/main 分支已清理，auto-improve 分支滞后）**
- 删除 `self._executor = None` 和 `self._poll_job = None`（未使用属性）
- 删除 `_setup_poll_callback()` 中的 `repeating_poll` 内部函数（复杂 executor 轮询逻辑已废弃）
- 简化 `_setup_poll_callback()` 为直接调用 `maya.utils.executeDeferred(lambda: None)`
- `_setup_executor()` 保留（作为占位符，测试覆盖），`_enable_executor` 保留（控制 poll callback 开关）

**阶段 2 - 测试文件清理**
- `test_server_coverage.py`：删除 `TestRepeatingPollClosure` 测试类（3 个测试，测试已删除的 repeating_poll 逻辑）
- `test_server_extended.py`：更新 `test_setup_executor_is_noop`，删除 `assert server._executor is None`（属性已不存在）
- 删除 `src/dcc_mcp_maya/actions/` 目录（僵尸文件，origin/main 已删除，auto-improve worktree 遗留）
- 删除 `tests/test_actions_round15~22.py`（7 个旧 actions 测试文件，从未加入 auto-improve git 追踪）

### 质量门禁
- ruff check src/ tests/：✅ All checks passed
- pytest 1397 tests：✅ All passed (1.91s)（基线维持，无退化）
- 推送：`13071d7..f7ae60a auto-improve -> auto-improve` ✅

### 下一轮关注点
- `list_skills()` 兼容层 `hasattr(summary, "name") else summary["name"]`：等待 dcc_mcp_core 实际返回 SkillSummary 后可简化
- `_setup_executor()` 和 `_setup_poll_callback()` 占位符方法：待 origin/main 确认不再需要后可完全移除
- test_actions_round10~14、test_actions_round19、test_actions_round23 等文件仍在主 workspace（feat/skills-sop），与 auto-improve 分支的 skills 架构不一致，下一轮需对齐
