---
layout: home

hero:
  name: dcc-mcp-maya
  text: AI 驱动的 Maya 自动化
  tagline: 将符合标准的 MCP 服务器直接嵌入 Maya — 让 AI Agent 完整控制你的三维工作流。
  image:
    src: /logo.svg
    alt: dcc-mcp-maya
  actions:
    - theme: brand
      text: 快速开始
      link: /zh/guide/getting-started
    - theme: alt
      text: 在 GitHub 查看
      link: https://github.com/loonghao/dcc-mcp-maya

features:
  - icon: 🤖
    title: 原生 MCP 协议
    details: 实现 2025-03-26 版 MCP Streamable HTTP 规范，兼容 Claude Desktop、Cursor、OpenClaw 及任意 MCP 宿主。
  - icon: 🎬
    title: 370+ MCP 工具
    details: 内置 64 个 Skill 包，覆盖场景管理、几何体、材质、动画、灯光、渲染、绑定、UV 操作等能力。
  - icon: 📸
    title: 视口截图
    details: 一次 MCP 调用即可将任意 Maya 视口捕获为 base64 编码的 PNG 图像，完美支持 AI 视觉反馈循环。
  - icon: 🔌
    title: 零外部依赖
    details: 无需网关进程，无需 IPC 桥接 — HTTP 服务器直接运行在 Maya 内嵌的 Python 解释器中。
  - icon: ⚡
    title: Skill 架构
    details: 热重载 Skill 包。通过 DCC_MCP_MAYA_SKILL_PATHS 发布自定义 Skill，无需修改核心代码。
  - icon: 🐍
    title: Maya 2020+ / Python 3.7+
    details: 已在 Maya 2020、2022、2023、2024、2025 上测试，支持 Python 3.7 至 3.12。
---
