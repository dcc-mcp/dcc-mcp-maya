---
layout: home

hero:
  name: dcc-mcp-maya
  text: AI 驱动的 Maya 自动化
  tagline: 将符合标准的 MCP 服务器直接嵌入 Maya，提供渐进式 typed tools，并可按需启用 sidecar 运行时。
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
    title: 160+ Typed Maya 工具
    details: 内置 23 个 Maya Skill 包，覆盖场景管理、几何体、材质、动画、灯光绑定、渲染、绑定、UV、交换与管线工作流。
  - icon: 📸
    title: 视口截图
    details: 一次 MCP 调用即可将任意 Maya 视口捕获为 base64 编码的 PNG 图像，完美支持 AI 视觉反馈循环。
  - icon: 🔌
    title: 默认进程内运行
    details: HTTP 服务器默认嵌入 Maya；插件部署可按需启用 dcc-mcp-server sidecar，将运行时与 Maya UI 线程隔离。
  - icon: ⚡
    title: 渐进式 Skill 架构
    details: 启动时保持精简工具面，通过 dcc_capability_manifest 发现未加载能力，再按需加载领域 Skill。
  - icon: 🐍
    title: Maya 2020+ / Python 3.7+
    details: 支持 Maya 内嵌 Python 3.7+ 运行时，模块包覆盖 Maya 2022 至 2026。
---
