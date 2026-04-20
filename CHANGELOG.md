# Changelog

## [0.2.10](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.9...v0.2.10) (2026-04-20)


### Features

* **skills:** add ToolAnnotations and SkillGroup to all 64 skills ([c4de362](https://github.com/loonghao/dcc-mcp-maya/commit/c4de362a5be836b393f3133aea24931838946ba3))


### Bug Fixes

* **test:** update test_skills_round34 for ToolAnnotations/SkillGroup SKILL.md format ([57ece68](https://github.com/loonghao/dcc-mcp-maya/commit/57ece683b479ebdbe578a755fdd2b592df810514))

## [0.2.9](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.8...v0.2.9) (2026-04-20)


### Features

* **dispatcher:** add MayaUiDispatcher + MayaUiPump + MayaStandaloneDispatcher ([6c78c99](https://github.com/loonghao/dcc-mcp-maya/commit/6c78c997326c3b94210998e0292fa5cd3e95cbae)), closes [#66](https://github.com/loonghao/dcc-mcp-maya/issues/66)


### Bug Fixes

* **plugin:** export DCC_MCP_PYTHON_EXECUTABLE / init snippet before server start ([f91f1be](https://github.com/loonghao/dcc-mcp-maya/commit/f91f1be458a66e2b5456787119e89da03829fd36)), closes [#63](https://github.com/loonghao/dcc-mcp-maya/issues/63)
* **server:** restore module-level _server_instance for plugin compatibility ([6480127](https://github.com/loonghao/dcc-mcp-maya/commit/6480127c06d99e1decc618edc1d15782376eb889))
* **tests:** relax maya-scene tool assertion for progressive loading ([#71](https://github.com/loonghao/dcc-mcp-maya/issues/71)) ([399b32c](https://github.com/loonghao/dcc-mcp-maya/commit/399b32c3c8f98c08237ae7bf2eb5e442dcab7d62))
* **test:** update E2E tool name assertions for core 0.13+ naming convention ([b13ab6c](https://github.com/loonghao/dcc-mcp-maya/commit/b13ab6c87dc43c5f3ebbbc86837b6df4b059498f))
* **test:** update tool name assertions for core 0.13+ naming convention ([429eba2](https://github.com/loonghao/dcc-mcp-maya/commit/429eba2fba1e6c544870289b67af3b799851fc6f))


### Code Refactoring

* align with dcc-mcp-core 0.13 API ([31abc6f](https://github.com/loonghao/dcc-mcp-maya/commit/31abc6f2c9e94692375b8f158a67a65532e47d35))

## [0.2.8](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.7...v0.2.8) (2026-04-16)


### Code Refactoring

* use DccServerBase from dcc-mcp-core ([#54](https://github.com/loonghao/dcc-mcp-maya/issues/54)) ([b94c4cc](https://github.com/loonghao/dcc-mcp-maya/commit/b94c4cca7b63d73e9d63abc8197651677916b85b))

## [0.2.7](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.6...v0.2.7) (2026-04-15)


### Features

* **docker:** Add Docker-based multi-version Maya testing support ([683eeb4](https://github.com/loonghao/dcc-mcp-maya/commit/683eeb4f4a02aa4dcc6024e27aa1d0511dfefbc4))
* **hotreload:** automatic skill hot-reload without server restart ([85c81ca](https://github.com/loonghao/dcc-mcp-maya/commit/85c81ca3d202e3caf72cea4f5923e79c9bfbf671))
* **plugin:** default gateway mode + non-blocking restart + startup banner ([1b4b98f](https://github.com/loonghao/dcc-mcp-maya/commit/1b4b98f0adc5a70fa17d3d1ae436ff1a131905b7))
* **server:** add gateway support + rename plugin to fix namespace collision ([17e23e1](https://github.com/loonghao/dcc-mcp-maya/commit/17e23e1056fa16e7dd370a4cfadd0efb2cec76ad))
* **server:** auto-include dcc-mcp-core bundled skills by default ([2224c25](https://github.com/loonghao/dcc-mcp-maya/commit/2224c25f94e5a40309fa827aa92e05a6b5bda493))
* **server:** register diagnostic IPC handlers for dcc-diagnostics skill ([bd3e1dc](https://github.com/loonghao/dcc-mcp-maya/commit/bd3e1dcdc1ae98c077674f99a2358d3bb0b5e1b4))


### Bug Fixes

* Add mayapy availability check and lint fixes for CI ([e03e619](https://github.com/loonghao/dcc-mcp-maya/commit/e03e619fe6e3e3810d8464b3305d3c604c104623))
* Apply ruff format to resolve formatting issues ([72175e1](https://github.com/loonghao/dcc-mcp-maya/commit/72175e1861e4bececba1f30a312c9a0af74d2462))
* **ci:** exclude integration tests from standard CI run ([3e7a267](https://github.com/loonghao/dcc-mcp-maya/commit/3e7a2673e73b51665af1dc00eb84cb82f93e7d54))
* **ci:** fix e2e PYTHONPATH expansion and narrow test collection ([90edb81](https://github.com/loonghao/dcc-mcp-maya/commit/90edb81d4e1d26cd64da648a442340db5877693f))
* **ci:** fix SSL certificate failure in assemble step on Maya 2022/2023 ([5d7c6d4](https://github.com/loonghao/dcc-mcp-maya/commit/5d7c6d4c4befb8eb486ec91674d3c0220dd2de15))
* **ci:** format diagnostics.py and fix test_start_server assertion ([b1bd133](https://github.com/loonghao/dcc-mcp-maya/commit/b1bd13350acc147c9795696883c481d13d5e3e96))
* **ci:** install pytest deps into mayapy before running e2e tests ([762b164](https://github.com/loonghao/dcc-mcp-maya/commit/762b16456596ebbf476c9627f6f18e38c37c4bca))
* **e2e:** lazy-import requests in GatewayTestClient to fix E2E conftest loading ([5eac8e8](https://github.com/loonghao/dcc-mcp-maya/commit/5eac8e81ff6f3d1f98adb9d63953072c509a3faa))
* **packaging:** ensure packaged .mod module works in Maya standalone/batch mode ([d1cebd8](https://github.com/loonghao/dcc-mcp-maya/commit/d1cebd874241a0c5ce851f21ce728f4ec0c63302))
* Remove unused imports and blank line whitespace ([0c5edee](https://github.com/loonghao/dcc-mcp-maya/commit/0c5edee4fe85478575a02c013fbf718775b08569))
* resolve CI failures and clean up repo ([82fa545](https://github.com/loonghao/dcc-mcp-maya/commit/82fa545f9c4f9896917b64227a5710340e954d38))
* Skip get_capabilities tests until method is implemented ([a07a8a2](https://github.com/loonghao/dcc-mcp-maya/commit/a07a8a2d7589abbb2fdd2b60b730e90f0eac4b3b))
* Skip test_skills_round44 when DccCapabilities unavailable ([dd0a3c8](https://github.com/loonghao/dcc-mcp-maya/commit/dd0a3c80a2fbdf956fa135defa9cd842faec31e5))
* Upgrade upload-artifact to v4 ([54623ff](https://github.com/loonghao/dcc-mcp-maya/commit/54623ffa0029bd6e31f47b57a60f6cef72d58700))


### Code Refactoring

* **packaging:** generate .mod file at install time from module-info.json ([58e8022](https://github.com/loonghao/dcc-mcp-maya/commit/58e8022bf36fe4040dcef1e20fb1c50affa11283))


### Documentation

* document bundled skills, IPC diagnostics, and include_bundled param ([3eb5ff4](https://github.com/loonghao/dcc-mcp-maya/commit/3eb5ff46234a802af900258ccb07ef1527ad088c))

## [0.2.6](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.5...v0.2.6) (2026-04-12)


### Bug Fixes

* **plugin:** use maya.api.OpenMaya (API 2.0) to resolve MFnPlugin AttributeError ([44f8170](https://github.com/loonghao/dcc-mcp-maya/commit/44f817038164be27f49d74c2af421fc1c72620e0))


### Code Refactoring

* **plugin:** add maya_useNewAPI(); simplify to direct API 2.0 import ([9020a89](https://github.com/loonghao/dcc-mcp-maya/commit/9020a890179e37bf71acd8614811d19468a40ec0))

## [0.2.5](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.4...v0.2.5) (2026-04-12)


### Features

* **api:** emit maya_warning on Arnold fallback in create_hdri_dome and create_render_pass; add test_skills_round42 (27 tests) ([8f11f4b](https://github.com/loonghao/dcc-mcp-maya/commit/8f11f4b84c2192e08fed7d072465b69fbf4d2e67))
* **api:** emit maya_warning on Arnold fallback in load_hdri; achieve 100% coverage (test_skills_round41) ([4ce6850](https://github.com/loonghao/dcc-mcp-maya/commit/4ce6850f5e9dde4091f8d71fceb0668aa9969bbb))
* **capabilities:** add DccCapabilities module, server.get_capabilities(), get_frame_range skill; fix test_round41 port conflict; add test_skills_round44 (47 tests) ([e6f9c2a](https://github.com/loonghao/dcc-mcp-maya/commit/e6f9c2a3cfe92ef361a76a51a69db471e01e348f))
* **server:** add is_skill_loaded, get_skill_info to MayaMcpServer; add test_skills_round45 (48 tests) ([401f0c4](https://github.com/loonghao/dcc-mcp-maya/commit/401f0c4fc6a541e76775424959d843b3e3e17f6a))
* **skills:** add mtoa plugin availability guards to all 5 maya-arnold-aov scripts; add test_skills_round43 (28 tests) ([b540188](https://github.com/loonghao/dcc-mcp-maya/commit/b540188a7f1865ba0c1e2624eee90003c4897045))


### Bug Fixes

* **release:** add workflow_dispatch input for manual build-mod; fix Python 3.14-&gt;3.12 ([22f54cc](https://github.com/loonghao/dcc-mcp-maya/commit/22f54cc20247b8621ef4df2b86e30a2892c8dda9))
* **release:** use inputs.tag_name as fallback for version/tag in manual workflow dispatch ([06a7c42](https://github.com/loonghao/dcc-mcp-maya/commit/06a7c42b247e550f0ea8ee64667b9ff7d1e423f2))
* **tests:** fix Python 3.7 compat and lint in test_skills_round45 ([c179cdc](https://github.com/loonghao/dcc-mcp-maya/commit/c179cdc3debf91638e70bba669b8e2828c214559))

## [0.2.4](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.3...v0.2.4) (2026-04-12)


### Bug Fixes

* **e2e:** fix deformer E2E tests and mark HTTP tool-call tests as xfail ([a4b29d0](https://github.com/loonghao/dcc-mcp-maya/commit/a4b29d04ab3ea733444c7279ea62822123923234))

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
