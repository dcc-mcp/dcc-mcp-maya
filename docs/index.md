---
layout: home

hero:
  name: dcc-mcp-maya
  text: AI-Powered Maya Automation
  tagline: Embed a standards-compliant MCP server directly inside Maya, with progressive typed tools and an optional sidecar runtime.
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
    title: 160+ Typed Maya Tools
    details: 23 Maya skill packages covering scene management, geometry, materials, animation, light rigs, rendering, rigging, UV operations, interchange and pipeline workflows.
  - icon: 📸
    title: Viewport Capture
    details: Capture any Maya viewport as a base64-encoded PNG with a single MCP call. Perfect for AI visual feedback loops.
  - icon: 🔌
    title: In-Process by Default
    details: The HTTP server runs embedded in Maya; plugin deployments can opt into the dcc-mcp-server sidecar when runtime isolation is useful.
  - icon: ⚡
    title: Progressive Skill Architecture
    details: Start with a compact minimal tool surface, discover unloaded capabilities with dcc_capability_manifest, then load domain skills on demand.
  - icon: 🐍
    title: Maya 2020+ / Python 3.7+
    details: Tested across Maya's embedded Python 3.7+ runtimes, including Maya 2022 through 2026 module packages.
---
