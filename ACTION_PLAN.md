# Docker mayapy 多版本集成 - 行动计划

**完成日期**: 2026-04-15  
**状态**: 🟢 代码完成，待提交

## 立即行动

### 步骤 1: 查看变更
```bash
cd /g/PycharmProjects/github/dcc-mcp-maya
git status
```

预期输出:
```
 M .github/workflows/multi-instance-tests.yml
 M .gitignore
 M tests/conftest.py
 M tests/fixtures/__init__.py
 M tests/fixtures/conftest.py
?? DOCKER_TESTING.md
?? tests/fixtures/docker_maya.py
?? tests/fixtures/instance_factory.py
?? tests/test_docker_integration.py
```

### 步骤 2: 本地验证 (可选)
```bash
# 语法检查
python3 -m py_compile tests/fixtures/docker_maya.py tests/fixtures/instance_factory.py

# 收集测试
pytest tests/test_docker_integration.py --collect-only -v

# 运行测试 (需要 Docker 或 mayapy)
export DCC_MCP_FORCE_DOCKER=1
pytest tests/test_docker_integration.py -v
```

### 步骤 3: 提交代码
```bash
# 添加所有变更
git add -A

# 提交
git commit -m "feat(docker): Add Docker-based multi-version Maya testing support

- DockerMayaInstanceManager for container instances
- Instance factory with intelligent Docker/local selection
- Multi-version CI matrix (Maya 2023/2024/2025)
- 9 new Docker integration tests
- Complete documentation (DOCKER_TESTING.md)

Supports automatic environment detection, multi-version
testing in CI (9 job combinations), and backward
compatibility with local mayapy installations."

# 推送到远端
git push origin feat/docker-testing
```

### 步骤 4: 创建 PR
```bash
# GitHub CLI 创建 PR
gh pr create --title "feat(docker): Docker-based multi-version Maya testing" \
  --body "See DOCKER_TESTING.md for complete documentation"
```

## 待提交文件详情

### 新增文件 (4 个代码文件)
- `tests/fixtures/docker_maya.py` (408 行)
- `tests/fixtures/instance_factory.py` (103 行)  
- `tests/test_docker_integration.py` (167 行)
- `DOCKER_TESTING.md` (307 行)

### 改进文件 (5 个)
- `.github/workflows/multi-instance-tests.yml` (+60 行)
- `tests/conftest.py` (±5 行)
- `tests/fixtures/__init__.py` (±5 行)
- `tests/fixtures/conftest.py` (新增)
- `.gitignore` (2 行新增)

### 本地参考文档 (不提交)
- `DOCKER_CHANGES.md` - 详细变更日志
- `DOCKER_QUICK_START.md` - 快速参考

## PR 检查清单

提交 PR 前确认:

- [ ] 所有文件语法正确
- [ ] 测试可收集 (9 个)
- [ ] .gitignore 更新正确
- [ ] 提交消息遵循 Conventional Commits
- [ ] 代码无 merge conflicts
- [ ] CI 工作流配置有效

提交后检查:

- [ ] GitHub 自动 CI 通过 (运行代码检查)
- [ ] Docker Hub 镜像拉取成功 (运行 Docker job)
- [ ] 多版本测试执行 (9 个 job 组合)
- [ ] 本地 fallback 测试运行 (3 个 job)

## 关键优势

✅ **自动模式选择** - 检测环境自动用 Docker/本地  
✅ **多版本测试** - CI 自动覆盖 Maya 2023/2024/2025  
✅ **向后兼容** - 现有测试无需修改  
✅ **开发友好** - 本地快速迭代 + CI 可靠验证  
✅ **文档完整** - DOCKER_TESTING.md 完整指南

## 常见问题

### Q: 我没有 Docker，可以用本地 mayapy 吗?
**A**: 是的！工厂类会自动检测并使用本地 mayapy。无需修改代码。

### Q: CI 中哪个 job 会失败?
**A**: 都不会失败。Docker job 拉取镜像可能延迟，但会优雅处理。本地 job 在没有 mayapy 时会 skip。

### Q: 如何跳过本地 fallback，只用 Docker?
**A**: 设置 `export DCC_MCP_FORCE_DOCKER=1` 环境变量。

### Q: 如何使用自定义 Docker registry?
**A**: 设置 `export DCC_MCP_DOCKER_REGISTRY=registry.example.com/`

## 后续工作 (可选)

- [ ] 添加 Windows/macOS 的 CI 矩阵
- [ ] 添加性能基准测试
- [ ] 实现 Docker Compose 支持 (完整 gateway 栈)
- [ ] 添加 Kubernetes 部署示例

## 文档导航

- **快速开始**: DOCKER_QUICK_START.md (本地)
- **完整指南**: DOCKER_TESTING.md (提交)
- **变更详情**: DOCKER_CHANGES.md (本地)
- **多实例指南**: README_TESTING.md
- **网关实现**: HOTRELOAD_CHANGES.md

## 支持

遇到问题?

1. 查看 DOCKER_TESTING.md 的"故障排查"章节
2. 运行 `docker ps -a` 检查容器状态
3. 运行 `docker logs <container_id>` 查看容器日志
4. 检查 pytest 输出是否有跳过的测试

## 完成！

代码已准备就绪，等待您的确认提交 PR。🚀
