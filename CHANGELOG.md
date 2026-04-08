# Changelog

## [0.2.0](https://github.com/loonghao/dcc-mcp-maya/compare/v0.1.0...v0.2.0) (2026-04-08)

### ⚠ BREAKING CHANGES

* Removes dcc-mcp-ipc and fastmcp dependencies. The MCP server now runs directly inside Maya using dcc-mcp-core's McpHttpServer.

### Features

* Refactor to new architecture — McpHttpServer embedded in Maya ([#8](https://github.com/loonghao/dcc-mcp-maya/issues/8))
* Add MayaMcpServer with DeferredExecutor for main-thread safety
* 14 built-in MCP tools: scene management, primitives, MEL/Python scripting
* Module-level start_server() / stop_server() convenience API
* Maya plugin with DCC MCP menu and auto-start on load

### Bug Fixes

* Ensure Python 3.7+ compatibility — Optional/List typing, tomllib backport ([#10](https://github.com/loonghao/dcc-mcp-maya/issues/10))
* Use ubuntu-22.04 for Python 3.7 CI runner ([#12](https://github.com/loonghao/dcc-mcp-maya/issues/12))

## 0.1.0 (2026-04-01)

### Features

* Initial release with Maya RPyC service and external MCP adapter
