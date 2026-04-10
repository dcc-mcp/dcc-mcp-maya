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

### 下一轮关注点
- `list_skills()` 返回 dict 兼容层：待 `dcc_mcp_core` 升级到实际返回 `SkillSummary` 后可简化为直接 `.name`
- `_maya_available()` 函数：仍在 `server.py` 中保留，供模块内部使用，不需要清理
- skills 脚本中的 `print(json.dumps(result))` 均在 `if __name__ == "__main__":` 守卫内，属于合理入口点
