---
layout: home

hero:
  name: dcc-mcp-maya
  text: AI-Powered Maya Automation
  tagline: Embed a standards-compliant MCP server directly inside Maya — let AI agents control your 3D workflow.
  image:
    src: /logo.svg
    alt: dcc-mcp-maya
  actions:
    - theme: brand
      text: Quick Start
      link: /guide/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/loonghao/dcc-mcp-maya

features:
  - icon: 🤖
    title: MCP Protocol Native
    details: Implements the 2025-03-26 MCP Streamable HTTP spec — compatible with Claude Desktop, Cursor, OpenClaw and any MCP host.
  - icon: 🎬
    title: 370+ MCP Tools
    details: 64 built-in skill packages covering scene management, geometry, materials, animation, lighting, rendering, rigging, UV operations and more.
  - icon: 📸
    title: Viewport Capture
    details: Capture any Maya viewport as a base64-encoded PNG with a single MCP call. Perfect for AI visual feedback loops.
  - icon: 🔌
    title: Zero External Dependencies
    details: No gateway process, no IPC bridge — the HTTP server runs embedded inside Maya's own Python interpreter.
  - icon: ⚡
    title: Skills Architecture
    details: Hot-reloadable skill packages. Ship your own skills via DCC_MCP_MAYA_SKILL_PATHS — no patch to the core required.
  - icon: 🐍
    title: Maya 2020+ / Python 3.7+
    details: Tested on Maya 2020, 2022, 2023, 2024, 2025. Works with Python 3.7 through 3.12.
---
