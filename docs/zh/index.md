---
layout: home

hero:
  name: "dcc-mcp-maya"
  text: "AI 驱动的 Maya 自动化"
  tagline: 将标准 MCP 服务器直接嵌入 Maya — 无需网关，无需额外进程。
  image:
    src: /logo.svg
    alt: dcc-mcp-maya
  actions:
    - theme: brand
      text: 快速开始
      link: /zh/guide/getting-started
    - theme: alt
      text: 在 GitHub 上查看
      link: https://github.com/loonghao/dcc-mcp-maya

features:
  - icon: 🤖
    title: MCP 协议原生支持
    details: 实现 2025-03-26 版本的 MCP Streamable HTTP 规范。任何兼容 MCP 的 AI 客户端（Claude Desktop、Cursor、OpenClaw）均可直接控制 Maya。

  - icon: 🎬
    title: 200+ 内置 Action
    details: 场景管理、几何体创建、材质、动画、绑定、动力学、渲染、UV、XGen、Bifrost — 组织为 28+ 个技能包。

  - icon: ⚡
    title: 零外部进程
    details: HTTP 服务器运行在 Maya 自身的 Python 解释器中，通过 Tokio 工作线程驱动。Maya API 调用通过 maya.utils 安全分发至主线程。

  - icon: 🔌
    title: 可扩展技能系统
    details: 在 DCC_MCP_MAYA_SKILL_PATHS 任意目录下放置 SKILL.md + scripts/ 即可注册自定义 Action，无需修改核心包。

  - icon: 🏗️
    title: 支持 Maya 2020+
    details: 兼容 Maya 2020 至 2026（Python 3.7–3.12）。通过 mayapy pip 安装或以 Maya 插件方式加载。

  - icon: 🌐
    title: 多客户端就绪
    details: 一个服务器，多个客户端同时连接。Claude Desktop、Cursor 等任意 MCP 兼容客户端均可同时使用。
---
