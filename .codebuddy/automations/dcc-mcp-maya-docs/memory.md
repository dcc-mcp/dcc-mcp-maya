# dcc-mcp-maya Docs Automation Memory

## Round 4 — 2026-04-10

### Status
COMPLETE — contributing.md 新建（英/中），核心 Action 参数表扩展，导航配置更新，构建通过，推送成功。

### 执行摘要
- 确认 `docs/` 中 22 个文件被 git 正常追踪（.gitignore 警告为历史遗留，不影响已追踪文件）
- 确认 `maya-scripting/scripts/` 中已有 `execute_mel.py` 和 `execute_python.py`（Round 2 担忧消除）
- 确认 `maya-namespaces`, `maya-texture-bake`, `maya-utility` 均有完整实现
- 从源码提取并补充了更多 Action 参数说明表
- 新建英/中 contributing 指南

### 完成内容

**扩展参数说明表（从源码 docstring 精确提取）：**
- `maya_scene__new_scene`：force
- `maya_scene__list_objects`：object_type, dag → returns context.objects, context.count
- `maya_scene__get_session_info`：无参数，返回字段完整列举
- `maya_primitives__set_transform`：object_name, translate, rotate, scale
- `maya_animation__get_keyframes`：object_name, attribute → returns context.keyframes
- `maya_animation__bake_simulation`：objects, start_frame, end_frame, sample_by
- `maya_materials__set_material_attribute`：material_name, attribute, value（支持 RGB 列表）
- `maya_rigging__create_joint`：name, position, parent
- `maya_scripting__execute_mel`：script → returns context.output
- `maya_scripting__execute_python`：code → returns context.output

**新建文件：**
- `docs/guide/contributing.md` — 英文贡献指南（技能包结构、注册方式、命名规则、测试方法、发布检查清单）
- `docs/zh/guide/contributing.md` — 中文同步版本
- `docs/.vitepress/config.ts` — 英/中侧边栏均添加 contributing 链接

### 构建验证
`vitepress build` 通过，2.34s，0 错误，22 个文档文件被 git 追踪。

### Git
提交：`13071d7 docs(guide): add contributing guide and expand action parameter tables`
推送：`8b19241..13071d7 auto-improve -> auto-improve`

### 当前文档站点状态
- 技能包：39 个（200+ Action）
- 参数说明表覆盖：16 个核心 Action
- 页面数：英/中各 guide（7 页）+ api（2 页）= 共约 18 个页面

### 下一轮待办（Round 5）
1. 修复 .gitignore 的 `docs` 条目（应为 `docs/.vitepress/dist`，而非 `docs/`），以消除 git add 警告
2. 为 `maya-uv-ops`, `maya-lighting`, `maya-cameras`, `maya-constraints`, `maya-references` 补充参数说明表
3. 在 `api/actions.md` 中更新示例（当前使用的是旧式 `dict` 返回，需对齐 `ActionResultModel`）
4. 添加 `snapshot.md` 和 `scene.md` 专题指南（任务书第二阶段遗留）
5. 考虑将 `auto-improve` 开 PR 到 `main`（已积累 32 个文档提交）
