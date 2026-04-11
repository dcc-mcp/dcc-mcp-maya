---
layout: home

hero:
  name: "dcc-mcp-maya"
  text: "AI-Powered Maya Automation"
  tagline: Embed a standards-compliant MCP server directly inside Maya — no gateway, no IPC process.
  image:
    src: /logo.svg
    alt: dcc-mcp-maya
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/loonghao/dcc-mcp-maya

features:
  - icon: 🤖
    title: MCP Protocol Native
    details: Implements the 2025-03-26 MCP Streamable HTTP specification. Any compatible AI host (Claude Desktop, Cursor, OpenClaw) can control Maya directly.

  - icon: 🎬
    title: 200+ Built-in Actions
    details: Scene management, geometry creation, materials, animation, rigging, dynamics, rendering, UV ops, XGen, Bifrost — organized into 28+ skill packages.

  - icon: ⚡
    title: Zero External Process
    details: The HTTP server runs inside Maya's own Python interpreter on a Tokio worker thread. Maya API calls are safely dispatched to the main thread via maya.utils.

  - icon: 🔌
    title: Extensible Skills
    details: Drop a SKILL.md + scripts/ directory anywhere on DCC_MCP_MAYA_SKILL_PATHS to register custom actions without touching the core package.

  - icon: 🏗️
    title: Maya 2020+ Support
    details: Works with Maya 2020 through 2026 (Python 3.7–3.12). Single pip install into mayapy or load as a Maya plugin.

  - icon: 🌐
    title: Multi-Host Ready
    details: One running server, many clients. Claude Desktop, Cursor, and any other MCP-compatible host can connect simultaneously.
---
