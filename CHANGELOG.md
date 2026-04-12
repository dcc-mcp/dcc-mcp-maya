# Changelog

## [0.2.3](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.2...v0.2.3) (2026-04-12)


### Features

* add skill discovery API, search-hint fields, and test rounds 35-40 ([8b6b96e](https://github.com/loonghao/dcc-mcp-maya/commit/8b6b96e113e47ce8d7a5b33d452560fda3bc3a19))
* add SKILL.md lint checker, fix merge conflicts, add pyyaml dev dep ([53cc48b](https://github.com/loonghao/dcc-mcp-maya/commit/53cc48b95f1423900ff26380b3fee024f1824ab8))
* **api:** add ensure_valid_name, build_context_dict, cross-DCC model helpers; feat(test): add conftest load_and_call helpers + test_skills_round10 (90 tests) ([188618c](https://github.com/loonghao/dcc-mcp-maya/commit/188618c13f72d12bc6ef5c63ff166a74aaf63b03))


### Bug Fixes

* **ci:** exclude packaging marker from default test run and fix lint issues ([5e36e76](https://github.com/loonghao/dcc-mcp-maya/commit/5e36e761154a36e3fb0a5628814c64339e6efcf3))
* **packaging:** replace pip download with PyPI JSON API for cross-platform wheel retrieval ([349da9a](https://github.com/loonghao/dcc-mcp-maya/commit/349da9a3acbbd677d7abcbecf8da73c669302b68))
* **packaging:** replace pip download with PyPI JSON API for cross-platform wheel retrieval ([0038aec](https://github.com/loonghao/dcc-mcp-maya/commit/0038aec9c8d4a6bb36d63b086d55fd9bb131b0ec))

## [0.2.2](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.1...v0.2.2) (2026-04-12)


### Features

* **ci:** add Maya .mod module distribution with offline packaging ([ce501d3](https://github.com/loonghao/dcc-mcp-maya/commit/ce501d3ee3c0b96602bbe99a0e6383353bb7299b))

## [0.2.1](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.0...v0.2.1) (2026-04-11)


### Features

* **api:** add batch_validate_nodes, require_any_param, get_param_list helpers; refactor skinning-utils to use validate_node_exists ([3165e0c](https://github.com/loonghao/dcc-mcp-maya/commit/3165e0cae3e8e9dadf51ad76057de2e873261d5b))
* **api:** add dcc_mcp_maya.api — unified skill authoring helpers ([932a2f5](https://github.com/loonghao/dcc-mcp-maya/commit/932a2f5daaa5383322f1f97bb2908ecb9dc6eb87))
* **api:** add require_param, validate_node_exists, validate_node_type helpers; add prompt= to all 172 skill scripts ([0262f49](https://github.com/loonghao/dcc-mcp-maya/commit/0262f497780d0d9d8eb9ef8f4ef412f5a07bdc69))
* migrate to release-please for automated versioning and PyPI publish ([#13](https://github.com/loonghao/dcc-mcp-maya/issues/13)) ([b4f1d5c](https://github.com/loonghao/dcc-mcp-maya/commit/b4f1d5cd633d35e358557bb2a345cdc0d642f53e))
* Skills-first architecture — inline scripts, remove actions layer, SkillCatalog API ([87929a5](https://github.com/loonghao/dcc-mcp-maya/commit/87929a590b782fad9ca125c3680acf9342439914))
* **skills:** add maya-annotation, maya-audio, maya-cache, maya-color-grading, maya-constraints-advanced skills ([1b3389a](https://github.com/loonghao/dcc-mcp-maya/commit/1b3389a6a05de7d5cc49c7825123106dee0049a0))
* **skills:** add maya-blend-shape-utils, maya-xform-utils, maya-spline-ik, maya-gpu-cache, maya-instancer skills ([0e04fb6](https://github.com/loonghao/dcc-mcp-maya/commit/0e04fb6335b61ceb537b8126aaa1c81596ba0fbb))
* **skills:** add maya-expressions scripts, maya-mocap, maya-muscle, maya-scene-assembly, maya-proxy-mesh skills ([2e9a699](https://github.com/loonghao/dcc-mcp-maya/commit/2e9a699020828aae422e3aee6d8539fbde0972fa))
* **skills:** add maya-fluid, maya-ocean, maya-cloth-sim, maya-grooming, maya-export-preset skills ([30f3283](https://github.com/loonghao/dcc-mcp-maya/commit/30f32835ed5bb463f76c0f5e0cfc567052ad22ca))
* **skills:** add maya-paint-effects, maya-hdri, maya-camera-sequence, maya-namespaces, maya-texture-bake skills ([5b20538](https://github.com/loonghao/dcc-mcp-maya/commit/5b20538cd68c02635a2203ce7a19d2f806661092))
* **skills:** add maya-scripting, maya-utility, maya-pipeline skills ([0a2aabd](https://github.com/loonghao/dcc-mcp-maya/commit/0a2aabd1ea1fd80004360499d6763a4377dc3843))
* **skills:** add maya-shot-export, maya-material-library, maya-toon, maya-nparticles, maya-render-farm skills ([7ef3d78](https://github.com/loonghao/dcc-mcp-maya/commit/7ef3d78d845a1749662b392eae8b30d69e492bab))
* **skills:** add maya-skinning-utils, maya-rig-utils, maya-render-passes, maya-pose-library, maya-light-rig skills ([63efa00](https://github.com/loonghao/dcc-mcp-maya/commit/63efa0007888cb7cb93e0f5973293a19cc553823))
* **skills:** migrate all 369 skill scripts to dcc_mcp_core.skill API ([aa44efa](https://github.com/loonghao/dcc-mcp-maya/commit/aa44efa691a267d0a20e349a5e1993d17dfd8d15))
* **skills:** Skills SOP — 179+ Maya MCP actions, E2E coverage, multi-instance tests ([b7b2ff7](https://github.com/loonghao/dcc-mcp-maya/commit/b7b2ff724a02c65541d065b83c6592150b51c69f))


### Bug Fixes

* **annotation:** use hasattr check for standalone cmds.annotate detection ([862173b](https://github.com/loonghao/dcc-mcp-maya/commit/862173be5916740134565af278003415b93c77a3))
* **ci:** use ubuntu-22.04 for Python 3.7 (ubuntu-latest is 24.04, dropped 3.7) ([#12](https://github.com/loonghao/dcc-mcp-maya/issues/12)) ([fe2897c](https://github.com/loonghao/dcc-mcp-maya/commit/fe2897cf9ebbecf5df6f260b76256055dea6eb9d))
* **e2e:** fix annotation, metadata, script node and Python 3.7 test failures ([0f8073c](https://github.com/loonghao/dcc-mcp-maya/commit/0f8073ca165c8613e5f60061c4f9309f356eab12))
* **e2e:** resolve all e2e test failures ([4f436fa](https://github.com/loonghao/dcc-mcp-maya/commit/4f436fa0b21c83298453c8a973991e67430112e2))
* ensure Python 3.7+ compatibility across all source files ([#10](https://github.com/loonghao/dcc-mcp-maya/issues/10)) ([8373258](https://github.com/loonghao/dcc-mcp-maya/commit/83732589314ed05a62ce4f57ea324a15e8cfaa44))
* **release:** use PERSONAL_ACCESS_TOKEN for release-please PR creation ([#16](https://github.com/loonghao/dcc-mcp-maya/issues/16)) ([2b39f1f](https://github.com/loonghao/dcc-mcp-maya/commit/2b39f1f0bb559dd6b3a5f7d9efda4f315ee3313f))
* **test:** force ImportError in test_with_maya_import_error via patch.dict ([594ebc6](https://github.com/loonghao/dcc-mcp-maya/commit/594ebc6c4ab08f16017e07d0e66962fe4a1522dd))


### Code Refactoring

* **api:** fix Python 3.7 type annotations; refactor 14 skill scripts to use validate_node_exists/batch_validate_nodes; add test_skills_round26 (61 tests) ([28b41f7](https://github.com/loonghao/dcc-mcp-maya/commit/28b41f762f1a111cc3cddab5e5c91000c93c6e21))
* **api:** replace hand-written objExists guards with validate_node_exists/batch_validate_nodes in maya-attributes, maya-scene, maya-uv-ops, maya-constraints, maya-materials (34 files, 36 objExists removed); add test_skills_round27 (42 tests) ([53fbeb3](https://github.com/loonghao/dcc-mcp-maya/commit/53fbeb39aa33438163e3a7b48caeccf827ed33dc))
* **server:** migrate to create_skill_manager API + remove dead executor code ([#23](https://github.com/loonghao/dcc-mcp-maya/issues/23)) ([9dd3777](https://github.com/loonghao/dcc-mcp-maya/commit/9dd3777ecab3d6f4ea0789e77fda0ca4be3b79bc))
* **skills:** bulk migrate 136 scripts from cmds.objExists to validate_node_exists; add test_skills_round29 (25 tests) ([ed47f02](https://github.com/loonghao/dcc-mcp-maya/commit/ed47f02413cf4d3e65b80cd59bc5793b0e4aea0c))
* **skills:** migrate 18 cmds.objExists guards to validate_node_exists; add test_skills_round31 (70 tests); fix ruff E741 in test_round30 ([b24b615](https://github.com/loonghao/dcc-mcp-maya/commit/b24b615d4d46ebe879a0bcf882750db55074cd16))
* **skills:** migrate 26 list-comp cmds.objExists to batch_validate_nodes; add test_skills_round32 (76 tests) ([8ffa31c](https://github.com/loonghao/dcc-mcp-maya/commit/8ffa31c28f5933a5e2b4cf1d833b61b8bf6eae69))
* **skills:** migrate 44 cmds.objExists guards to validate_node_exists/batch_validate_nodes; add test_skills_round30 (36 tests) ([63df941](https://github.com/loonghao/dcc-mcp-maya/commit/63df941e8cc8a3eb7cf1881f3fe3b08dc4cd595b))
* **skills:** migrate all 369 skill scripts to dcc_mcp_maya.api ([acbd6a6](https://github.com/loonghao/dcc-mcp-maya/commit/acbd6a61fa1c82636dfc6cad28eb0f68721d131a))
* **skills:** migrate maya-mash, maya-selection, maya-xgen 15 scripts to skill_entry style; update test_skills_round13 for new API; add test_skills_round28 (49 tests) ([038bd17](https://github.com/loonghao/dcc-mcp-maya/commit/038bd173a27f759d2e0f59a6a03e74863c7215e9))


### Documentation

* update docs site with adapter/scene/snapshot API pages and additional guides ([3e0f0a4](https://github.com/loonghao/dcc-mcp-maya/commit/3e0f0a47b458da2bef82e4c7dec5ccafbcc322a3))

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
