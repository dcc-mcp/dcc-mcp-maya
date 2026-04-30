# Changelog

## [0.2.21](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.20...v0.2.21) (2026-04-30)


### Features

* **server:** DCC_MCP_MAYA_STRICT_SKILL_SCAN + stale-aware discovery ([#144](https://github.com/loonghao/dcc-mcp-maya/issues/144)) ([9554dc8](https://github.com/loonghao/dcc-mcp-maya/commit/9554dc8da31bcd6cc58b55308e884e055c26f8b3))
* **server:** wire workflows + job recovery knobs ([#145](https://github.com/loonghao/dcc-mcp-maya/issues/145)) ([5548ff4](https://github.com/loonghao/dcc-mcp-maya/commit/5548ff4973f1f0d57702888c1060e7863e48b55a))


### Bug Fixes

* **deps:** bump dcc-mcp-core to 0.14.19 for three-tier gateway election ([#143](https://github.com/loonghao/dcc-mcp-maya/issues/143)) ([96bd336](https://github.com/loonghao/dcc-mcp-maya/commit/96bd336ca79d8440ea8e704522545c87bfa08b4e))
* **server:** wire in-process executor on dispatcher attach ([#142](https://github.com/loonghao/dcc-mcp-maya/issues/142)) ([89123ea](https://github.com/loonghao/dcc-mcp-maya/commit/89123ea07a08e2e6d0f1735ec4a7fa4085f29b4f))


### Documentation

* **agents:** link upstream dcc-mcp-core llms.txt as authoritative API reference ([#134](https://github.com/loonghao/dcc-mcp-maya/issues/134)) ([2de112f](https://github.com/loonghao/dcc-mcp-maya/commit/2de112f503e4a42c6ba382d73a793b18cea7148d))
* update skill count from 64 to 12 packages (73 scripts) ([#141](https://github.com/loonghao/dcc-mcp-maya/issues/141)) ([28ddd3c](https://github.com/loonghao/dcc-mcp-maya/commit/28ddd3c303aeb5628f482eb52150652e80765252))
* update version to 0.2.20 and add Rust-backed dispatcher documentation ([946026a](https://github.com/loonghao/dcc-mcp-maya/commit/946026ab7924ce7d438075bbc5e8175e8a08a1b6))
* update version to 0.2.20 and add Rust-backed dispatcher documentation ([b7b6ee0](https://github.com/loonghao/dcc-mcp-maya/commit/b7b6ee09d25f5272dd5902283b777f87bde99c07))

## [0.2.20](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.19...v0.2.20) (2026-04-29)


### Bug Fixes

* **plugin:** robust cleanup in uninitializePlugin + stale instance warning ([#130](https://github.com/loonghao/dcc-mcp-maya/issues/130)) ([042764c](https://github.com/loonghao/dcc-mcp-maya/commit/042764cdcdefb12be974755e8da9998e90cc8fa7))
* **pyexec:** auto-correct DCC_MCP_PYTHON_EXECUTABLE when set to a GUI binary ([#129](https://github.com/loonghao/dcc-mcp-maya/issues/129)) ([d1a0666](https://github.com/loonghao/dcc-mcp-maya/commit/d1a0666974ad479a2c3ade1207068ba6aa002781))


### Code Refactoring

* **dispatcher:** split dispatcher.py into a dispatcher/ directory module ([#131](https://github.com/loonghao/dcc-mcp-maya/issues/131)) ([be2e023](https://github.com/loonghao/dcc-mcp-maya/commit/be2e0230a10c83efe5d3c9ea534251a5393261fa))
* **server:** split MayaMcpServer per SRP into env / executor / loader / probe / transport modules ([#133](https://github.com/loonghao/dcc-mcp-maya/issues/133)) ([80601a0](https://github.com/loonghao/dcc-mcp-maya/commit/80601a0f5965d0fd13492fad9f8ff5373425e1ef))

## [0.2.19](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.18...v0.2.19) (2026-04-26)


### Bug Fixes

* **executor:** replace catalog.set_in_process_executor with register_handler for core 0.14.14 ([0e7885d](https://github.com/loonghao/dcc-mcp-maya/commit/0e7885d78e2da76c701180dd88a1a686ab69a757)), closes [#122](https://github.com/loonghao/dcc-mcp-maya/issues/122)
* **lint:** remove unused call import and fix import order in test_skills_round46 ([f762092](https://github.com/loonghao/dcc-mcp-maya/commit/f762092e870dfb4198295bb4d8a0003a2042b3f3))

## [0.2.18](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.17...v0.2.18) (2026-04-26)


### Features

* add defaults block to all skill tools.yaml files ([c5926d6](https://github.com/loonghao/dcc-mcp-maya/commit/c5926d63a12a574e7231693e8d571a83d4ee555f))
* **skills:** add defaults block to tools.yaml for DRY configuration ([bce59f1](https://github.com/loonghao/dcc-mcp-maya/commit/bce59f15763432d245ac14038f8f7a1d7503abfa))
* **skills:** add Maya introspect provider + OpenMaya per-version index ([#117](https://github.com/loonghao/dcc-mcp-maya/issues/117), [#115](https://github.com/loonghao/dcc-mcp-maya/issues/115)) ([b8adaa1](https://github.com/loonghao/dcc-mcp-maya/commit/b8adaa1b1dda92a2c4e93cf3b38e10c68657fb5a))
* **skills:** elevate maya-scripting as primary fall-through entry (bitter-lesson) ([2a93266](https://github.com/loonghao/dcc-mcp-maya/commit/2a932662c5e3bef868cc8fe217bf69ee64d8d6da)), closes [#114](https://github.com/loonghao/dcc-mcp-maya/issues/114)


### Bug Fixes

* align with dcc-mcp-core 0.14.13 API (find_skills -&gt; search_skills) ([e4eae4a](https://github.com/loonghao/dcc-mcp-maya/commit/e4eae4a7ca0de3e809d5faa623e9644f768d5db8))
* **ci:** fix ruff I001 import order and annotator idempotency ([a3a262e](https://github.com/loonghao/dcc-mcp-maya/commit/a3a262e0fe6b93fb4b2905c54e864be0a56ac75f))
* **server:** correctly call main(**params) in in-process executor ([#108](https://github.com/loonghao/dcc-mcp-maya/issues/108)) ([38b0f24](https://github.com/loonghao/dcc-mcp-maya/commit/38b0f24a8b664b677fd46e61590603613b0e3f84))
* set non-core tool groups to default_active: false for progressive exposure ([4e83d19](https://github.com/loonghao/dcc-mcp-maya/commit/4e83d19034ab3dc5d7ed61f386972ddb40f5dfd2))
* **tests:** make search_skills mock assertions Python 3.7 compatible ([7d283f1](https://github.com/loonghao/dcc-mcp-maya/commit/7d283f151f3586d91cbf6f759ef2bd303fedbb0a))
* **test:** update e2e test for progressive skill/group loading ([3fd597f](https://github.com/loonghao/dcc-mcp-maya/commit/3fd597fa4c86581021f79d0e8459b7c141ee15aa))
* **test:** use correct param name for activate_tool_group ([3d590cb](https://github.com/loonghao/dcc-mcp-maya/commit/3d590cb9e11c4b3c32849e427822145badfb5ed7))


### Code Refactoring

* reduce bundled skills from 64 to 12 core pipeline skills ([04d0c65](https://github.com/loonghao/dcc-mcp-maya/commit/04d0c65fc321b88cdc4a838a932d2dede2e8f72d))
* **test:** split progressive-loading test into two focused tests ([c495f45](https://github.com/loonghao/dcc-mcp-maya/commit/c495f45ea706bbf2610044e8c520f13253ddcf8e))

## [0.2.17](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.16...v0.2.17) (2026-04-24)


### Bug Fixes

* **server:** clear job_storage_path when empty string disables persistence ([f8f2dd8](https://github.com/loonghao/dcc-mcp-maya/commit/f8f2dd8180d85187fbdda4b9358a15ca5edc122f))


### Documentation

* remove stale skill_executor references; fix plugin path in AGENTS ([ec1c76c](https://github.com/loonghao/dcc-mcp-maya/commit/ec1c76c5db2168e271bc65154037b82773304b84))

## [0.2.16](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.15...v0.2.16) (2026-04-23)


### Documentation

* add AI-friendly documentation and fix VitePress navigation ([9eb4258](https://github.com/loonghao/dcc-mcp-maya/commit/9eb42589295f05a002609990ffcfa1a0d47b7935))

## [0.2.15](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.14...v0.2.15) (2026-04-22)


### Features

* **skills:** implement layered skill architecture with explicit routing ([#100](https://github.com/loonghao/dcc-mcp-maya/issues/100)) ([acd6c7c](https://github.com/loonghao/dcc-mcp-maya/commit/acd6c7cd2bc27b5a438ae6f9ee4a43dafe9ecfdf))

## [0.2.14](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.13...v0.2.14) (2026-04-22)


### Features

* **dispatcher:** add submit_async_callable + gateway integration tests ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85) [#86](https://github.com/loonghao/dcc-mcp-maya/issues/86) [#88](https://github.com/loonghao/dcc-mcp-maya/issues/88)) ([30f984a](https://github.com/loonghao/dcc-mcp-maya/commit/30f984a7e85c6cd5fc83948c98e284ab3914c6a2))
* **server:** wire Prometheus metrics, job persistence, and gateway routing ([#86](https://github.com/loonghao/dcc-mcp-maya/issues/86), [#87](https://github.com/loonghao/dcc-mcp-maya/issues/87), [#89](https://github.com/loonghao/dcc-mcp-maya/issues/89)) ([e1c5cf3](https://github.com/loonghao/dcc-mcp-maya/commit/e1c5cf31c55efde9d963904819a01f03c34d1cbe))
* **skills:** maya-render-farm honours cooperative cancellation ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85)) ([a993e76](https://github.com/loonghao/dcc-mcp-maya/commit/a993e76dd33d1620eefaf5a77016da792f2b02a4))

## [0.2.13](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.12...v0.2.13) (2026-04-22)


### Features

* **dispatcher:** cooperative cancellation + pump overrun stats ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85)) ([6d76e18](https://github.com/loonghao/dcc-mcp-maya/commit/6d76e18b675013b9205a5ff2684520937f90de3e))
* **server:** drain attached MayaUiDispatcher on stop() ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85), [#89](https://github.com/loonghao/dcc-mcp-maya/issues/89)) ([42d9a02](https://github.com/loonghao/dcc-mcp-maya/commit/42d9a020368fb774c78d3028f67c852f7d498b71))
* **skills:** annotate bundled tools.yaml with execution/affinity ([#84](https://github.com/loonghao/dcc-mcp-maya/issues/84)) ([#91](https://github.com/loonghao/dcc-mcp-maya/issues/91)) ([f0e2c54](https://github.com/loonghao/dcc-mcp-maya/commit/f0e2c5490ad8386750cdac662bbc6cf4ccb9619a))


### Bug Fixes

* **tests:** update E2E assertions for bare tool names (dcc-mcp-core 0.14.1+) ([2ba0843](https://github.com/loonghao/dcc-mcp-maya/commit/2ba084321062e7b0dc56b24671a8ac057652329c))


### Code Refactoring

* **skills:** migrate all skills to sibling-file pattern (dcc-mcp-core [#356](https://github.com/loonghao/dcc-mcp-maya/issues/356)) ([#90](https://github.com/loonghao/dcc-mcp-maya/issues/90)) ([1456661](https://github.com/loonghao/dcc-mcp-maya/commit/145666179b948e7b19bc815b87db023ab9883145))


### Documentation

* multi-Maya-instance deployment on a single workstation ([#88](https://github.com/loonghao/dcc-mcp-maya/issues/88)) ([#92](https://github.com/loonghao/dcc-mcp-maya/issues/92)) ([10893eb](https://github.com/loonghao/dcc-mcp-maya/commit/10893eb55516bb7d5c997c037f54db1276801b49))

## [0.2.12](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.11...v0.2.12) (2026-04-21)


### Features

* add minimal-mode default tool surface with progressive loading ([#80](https://github.com/loonghao/dcc-mcp-maya/issues/80)) ([b73379f](https://github.com/loonghao/dcc-mcp-maya/commit/b73379fee3213d2f39147bd25b0b62d38fe368a1))


### Bug Fixes

* **ci:** update e2e.yml for new assemble output paths ([b18ec68](https://github.com/loonghao/dcc-mcp-maya/commit/b18ec687836b635fda149baca2556476f3586671))


### Code Refactoring

* **packaging:** rewrite install scripts and add portable/pipeline ZIP variants ([4f9228c](https://github.com/loonghao/dcc-mcp-maya/commit/4f9228c2e3d7587ed0bc2c41a83d89285268ecf3))

## [0.2.11](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.10...v0.2.11) (2026-04-20)


### Bug Fixes

* **tests:** relax tool assertions for progressive skill loading ([#77](https://github.com/loonghao/dcc-mcp-maya/issues/77)) ([5a0f407](https://github.com/loonghao/dcc-mcp-maya/commit/5a0f407308c1759cc7578d5ed9eb78becc36311c))
* update justfile to use create_skill_server (renamed in core 0.13+) ([#74](https://github.com/loonghao/dcc-mcp-maya/issues/74)) ([4979239](https://github.com/loonghao/dcc-mcp-maya/commit/4979239ef9c1350f005a71a5f29a331ee6ce4360))

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
