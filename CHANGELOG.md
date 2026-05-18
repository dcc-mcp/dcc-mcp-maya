# Changelog

## [0.3.1](https://github.com/loonghao/dcc-mcp-maya/compare/v0.3.0...v0.3.1) (2026-05-18)


### Bug Fixes

* harden maya small failure paths ([972a01f](https://github.com/loonghao/dcc-mcp-maya/commit/972a01fdd9a93dfad3241bbe66897cc37ff79920))
* quiet maya ci metadata warnings ([7ee7b66](https://github.com/loonghao/dcc-mcp-maya/commit/7ee7b663847dc64aa4a3e317e5c08eb549c81303))


### Documentation

* add README status badges ([4deb7b9](https://github.com/loonghao/dcc-mcp-maya/commit/4deb7b90aa8e08bae7798f6e1ce5ce1f3ac6c1d9))
* update architecture documentation ([d243669](https://github.com/loonghao/dcc-mcp-maya/commit/d243669a11f8677e622ddca306873327d9927852))

## [0.3.0](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.29...v0.3.0) (2026-05-17)


### ⚠ BREAKING CHANGES

* Removes dcc-mcp-ipc and fastmcp dependencies. The MCP server now runs directly inside Maya using dcc-mcp-core's McpHttpServer (MCP 2025-03-26 Streamable HTTP spec).

### Features

* add defaults block to all skill tools.yaml files ([3184be5](https://github.com/loonghao/dcc-mcp-maya/commit/3184be545b5acfa7ae433e0b2482efe0174e4fa3))
* add maya-link/maya-unlink/maya-dev recipes for local development ([c043af9](https://github.com/loonghao/dcc-mcp-maya/commit/c043af9c61461b1a01313fa83c95c7decacacbd2))
* add minimal-mode default tool surface with progressive loading ([#80](https://github.com/loonghao/dcc-mcp-maya/issues/80)) ([a4b8034](https://github.com/loonghao/dcc-mcp-maya/commit/a4b8034bc452184d1d62d71b8a4a0bbd172602a1))
* add skill discovery API, search-hint fields, and test rounds 35-40 ([ec04b4a](https://github.com/loonghao/dcc-mcp-maya/commit/ec04b4a290ac001c266d5dcc95aca3174265521a))
* add SKILL.md lint checker, fix merge conflicts, add pyyaml dev dep ([26c20ba](https://github.com/loonghao/dcc-mcp-maya/commit/26c20bad4c491625bd894f035e581b24a261c6d6))
* adopt core host dispatcher for Maya skills ([#177](https://github.com/loonghao/dcc-mcp-maya/issues/177)) ([c826faa](https://github.com/loonghao/dcc-mcp-maya/commit/c826faa1ca3ddbff2f0e6fb4f4b08fa796a5047e)), closes [#136](https://github.com/loonghao/dcc-mcp-maya/issues/136) [#173](https://github.com/loonghao/dcc-mcp-maya/issues/173) [#176](https://github.com/loonghao/dcc-mcp-maya/issues/176)
* **api:** add batch_validate_nodes, require_any_param, get_param_list helpers; refactor skinning-utils to use validate_node_exists ([5510a1b](https://github.com/loonghao/dcc-mcp-maya/commit/5510a1b46a12c82e29ad6769f9ff30cbc24243da))
* **api:** add dcc_mcp_maya.api — unified skill authoring helpers ([24ff160](https://github.com/loonghao/dcc-mcp-maya/commit/24ff1602920405f3a119e6c7318a4c7c6398f514))
* **api:** add ensure_valid_name, build_context_dict, cross-DCC model helpers; feat(test): add conftest load_and_call helpers + test_skills_round10 (90 tests) ([ff6e8e2](https://github.com/loonghao/dcc-mcp-maya/commit/ff6e8e2e2b1f286b5f8395833be10d41f50f1db1))
* **api:** add require_param, validate_node_exists, validate_node_type helpers; add prompt= to all 172 skill scripts ([eb5387f](https://github.com/loonghao/dcc-mcp-maya/commit/eb5387f2839ae411553fd3bb5d41e6ed28cbcb0d))
* **api:** emit maya_warning on Arnold fallback in create_hdri_dome and create_render_pass; add test_skills_round42 (27 tests) ([6ac6ed4](https://github.com/loonghao/dcc-mcp-maya/commit/6ac6ed41dfbdf71eadfaedba47a49f27e3303544))
* **api:** emit maya_warning on Arnold fallback in load_hdri; achieve 100% coverage (test_skills_round41) ([45c4f2e](https://github.com/loonghao/dcc-mcp-maya/commit/45c4f2e980c657379101aed643f4564741bc1348))
* **capabilities:** add DccCapabilities module, server.get_capabilities(), get_frame_range skill; fix test_round41 port conflict; add test_skills_round44 (47 tests) ([7081b96](https://github.com/loonghao/dcc-mcp-maya/commit/7081b96c5b53fe1a364a6b7861eb68dac5bcdad8))
* **capability:** publish unloaded skills in capability manifest ([#178](https://github.com/loonghao/dcc-mcp-maya/issues/178)) ([2b66124](https://github.com/loonghao/dcc-mcp-maya/commit/2b661243ad9870069e0abae0de78a7c931b040cc)), closes [#174](https://github.com/loonghao/dcc-mcp-maya/issues/174)
* **ci:** add Maya .mod module distribution with offline packaging ([ecdf1b5](https://github.com/loonghao/dcc-mcp-maya/commit/ecdf1b5218855238fdf3820c2cb5cbbfa1921efa))
* **core-0.14.22:** wire tool_exposure + cursor-safe names, typed output helper ([#172](https://github.com/loonghao/dcc-mcp-maya/issues/172)) ([bf1f617](https://github.com/loonghao/dcc-mcp-maya/commit/bf1f61769fead1c64a1c1af05d149e1b514dea31))
* **dispatcher:** add MayaUiDispatcher + MayaUiPump + MayaStandaloneDispatcher ([2d1c869](https://github.com/loonghao/dcc-mcp-maya/commit/2d1c8695f780cd3f64c5058707e2e54768f0f961)), closes [#66](https://github.com/loonghao/dcc-mcp-maya/issues/66)
* **dispatcher:** add submit_async_callable + gateway integration tests ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85) [#86](https://github.com/loonghao/dcc-mcp-maya/issues/86) [#88](https://github.com/loonghao/dcc-mcp-maya/issues/88)) ([62cb6dc](https://github.com/loonghao/dcc-mcp-maya/commit/62cb6dc0a65f5e9515ab04b341a241b6c7d3a267))
* **dispatcher:** cooperative cancellation + pump overrun stats ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85)) ([0be12e1](https://github.com/loonghao/dcc-mcp-maya/commit/0be12e1e8bc0fe9bb9623633d24ae101ce37764c))
* **docker:** Add Docker-based multi-version Maya testing support ([39a757b](https://github.com/loonghao/dcc-mcp-maya/commit/39a757bccc7b253d66578ba3d7f7c66ea6cf160e))
* **execute_python:** auto-marshal user code onto Maya's main thread ([e741a3c](https://github.com/loonghao/dcc-mcp-maya/commit/e741a3c5678553263136583c2696218bba93e3dc))
* **execute_python:** single-writer queue for concurrent main-thread marshalling ([edcbd49](https://github.com/loonghao/dcc-mcp-maya/commit/edcbd497a24a15f5e18d3553fce22a6d908c94ef))
* **executor:** universal main-thread safety net + affinity field enforcement ([06f6a92](https://github.com/loonghao/dcc-mcp-maya/commit/06f6a923ac06f28ba1f653e960e8c443602ea63a))
* **gateway:** compact capability manifest + context snapshot ([#163](https://github.com/loonghao/dcc-mcp-maya/issues/163), [#164](https://github.com/loonghao/dcc-mcp-maya/issues/164), [#165](https://github.com/loonghao/dcc-mcp-maya/issues/165)) ([#166](https://github.com/loonghao/dcc-mcp-maya/issues/166)) ([a04158f](https://github.com/loonghao/dcc-mcp-maya/commit/a04158ffff8902c98763f113d4080944fea19437))
* **hotreload:** automatic skill hot-reload without server restart ([39adb42](https://github.com/loonghao/dcc-mcp-maya/commit/39adb4287cc64698c5fde7a4d6b4b9546d1bd9b7))
* migrate to release-please for automated versioning and PyPI publish ([#13](https://github.com/loonghao/dcc-mcp-maya/issues/13)) ([b40acb1](https://github.com/loonghao/dcc-mcp-maya/commit/b40acb1af1a1425df0865ce6e746a8899f242001))
* **plugin:** default gateway mode + non-blocking restart + startup banner ([978069b](https://github.com/loonghao/dcc-mcp-maya/commit/978069b42a8caf7dad2a8a30b2052ddf8d69032a))
* **plugin:** replace MCP menu items with OpenAPI docs and Admin panel links ([86c6649](https://github.com/loonghao/dcc-mcp-maya/commit/86c6649ead2edbaf12cb72160c3f497702b5c6d4))
* **project:** wire dcc-mcp-core register_project_tools into MayaMcpServer ([#576](https://github.com/loonghao/dcc-mcp-maya/issues/576)) ([#169](https://github.com/loonghao/dcc-mcp-maya/issues/169)) ([419bfa1](https://github.com/loonghao/dcc-mcp-maya/commit/419bfa109d1200188ea8ccd581d37bba334324fb))
* **queue:** wedge detection + drain_pending + io action=drain (auto-unwedge) ([aebb08b](https://github.com/loonghao/dcc-mcp-maya/commit/aebb08b72ea09faf057f25fed389a11053c88987))
* **readiness:** wire three-state ReadinessProbe into MayaMcpServer ([#184](https://github.com/loonghao/dcc-mcp-maya/issues/184)) ([#188](https://github.com/loonghao/dcc-mcp-maya/issues/188)) ([932d8ee](https://github.com/loonghao/dcc-mcp-maya/commit/932d8ee7a26d43c56d74dd8717c09e6ab9acb0cf))
* refactor to new architecture — McpHttpServer embedded in Maya ([#8](https://github.com/loonghao/dcc-mcp-maya/issues/8)) ([dca6180](https://github.com/loonghao/dcc-mcp-maya/commit/dca618054d8dc2a841ea949bbbb75ebf36cb6286))
* **resources:** wire Maya scene + producers into core 0.15.0 ResourceRegistry ([#187](https://github.com/loonghao/dcc-mcp-maya/issues/187)) ([#190](https://github.com/loonghao/dcc-mcp-maya/issues/190)) ([8feca51](https://github.com/loonghao/dcc-mcp-maya/commit/8feca51158dda7c30ed499ceb1e30aa810583541))
* **scripting:** spill long inline execute_python to host temp file ([0cf1b59](https://github.com/loonghao/dcc-mcp-maya/commit/0cf1b5997114d6aa514e5d609f268e7465e5cc78))
* **server:** add gateway support + rename plugin to fix namespace collision ([e4733ca](https://github.com/loonghao/dcc-mcp-maya/commit/e4733ca44f695e6b6069121a9cf3e7a73ded7ab9))
* **server:** add is_skill_loaded, get_skill_info to MayaMcpServer; add test_skills_round45 (48 tests) ([cb28026](https://github.com/loonghao/dcc-mcp-maya/commit/cb28026091db66c1105d7aab4654524c6bc41015))
* **server:** auto-include dcc-mcp-core bundled skills by default ([1318bc7](https://github.com/loonghao/dcc-mcp-maya/commit/1318bc7968d8d52c6ceaf6b35f2b0902cc0dfb88))
* **server:** DCC_MCP_MAYA_STRICT_SKILL_SCAN + stale-aware discovery ([#144](https://github.com/loonghao/dcc-mcp-maya/issues/144)) ([4eff2ee](https://github.com/loonghao/dcc-mcp-maya/commit/4eff2ee8a5d9878028f37d7f36536c529570b3b3))
* **server:** DCC_MCP_MAYA_STRICT_SKILL_SCAN + stale-aware discovery ([#144](https://github.com/loonghao/dcc-mcp-maya/issues/144)) ([c6e513a](https://github.com/loonghao/dcc-mcp-maya/commit/c6e513a4d48eec4265deca99ed4547d6f3269d99))
* **server:** drain attached MayaUiDispatcher on stop() ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85), [#89](https://github.com/loonghao/dcc-mcp-maya/issues/89)) ([664936f](https://github.com/loonghao/dcc-mcp-maya/commit/664936fd8755fed89416ed1503de2f643859619c))
* **server:** register diagnostic IPC handlers for dcc-diagnostics skill ([a17d038](https://github.com/loonghao/dcc-mcp-maya/commit/a17d038d609b28bb1eaa2ae73328ad97785d2f4e))
* **server:** wire Prometheus metrics, job persistence, and gateway routing ([#86](https://github.com/loonghao/dcc-mcp-maya/issues/86), [#87](https://github.com/loonghao/dcc-mcp-maya/issues/87), [#89](https://github.com/loonghao/dcc-mcp-maya/issues/89)) ([a348d36](https://github.com/loonghao/dcc-mcp-maya/commit/a348d364fcd0a467c6a713e1c2fa757f704b9ac7))
* **server:** wire workflows + job recovery knobs ([#145](https://github.com/loonghao/dcc-mcp-maya/issues/145)) ([355449c](https://github.com/loonghao/dcc-mcp-maya/commit/355449cc7e8f1f07f8151d0295df2b5c46df4b14))
* **server:** wire workflows + job recovery knobs ([#145](https://github.com/loonghao/dcc-mcp-maya/issues/145)) ([f73e4f7](https://github.com/loonghao/dcc-mcp-maya/commit/f73e4f7aaf63fefb0227af5d107536fc2b666421))
* **shutdown:** harden plugin for non-cooperative Maya exits ([#186](https://github.com/loonghao/dcc-mcp-maya/issues/186)) ([#189](https://github.com/loonghao/dcc-mcp-maya/issues/189)) ([148e931](https://github.com/loonghao/dcc-mcp-maya/commit/148e93111c7260fa0e54184eb4a7793e35e198bc))
* **sidecar:** Maya-side wire-frame dispatcher — closes the sidecar → DCC loop (RFC [#998](https://github.com/loonghao/dcc-mcp-maya/issues/998) Phase 2) ([#246](https://github.com/loonghao/dcc-mcp-maya/issues/246)) ([4800635](https://github.com/loonghao/dcc-mcp-maya/commit/480063561020da86ced163dfe0b99f9eaecc25a4))
* **sidecar:** opt-in dcc-mcp-server sidecar shim + Maya plug-in (RFC [#998](https://github.com/loonghao/dcc-mcp-maya/issues/998)) ([#244](https://github.com/loonghao/dcc-mcp-maya/issues/244)) ([375fac2](https://github.com/loonghao/dcc-mcp-maya/commit/375fac2a2483235a5ef39f20373367ae7447987e))
* **sidecar:** switch Maya wire to qtserver:// (RFC [#998](https://github.com/loonghao/dcc-mcp-maya/issues/998) Addendum B item 2) ([b92f746](https://github.com/loonghao/dcc-mcp-maya/commit/b92f746ff57b40d730c0d5d513544004878fe70c))
* Skills-first architecture — inline scripts, remove actions layer, SkillCatalog API ([e8a3aac](https://github.com/loonghao/dcc-mcp-maya/commit/e8a3aac8377dd30b18fe07f45a6259890d368811))
* **skills:** add defaults block to tools.yaml for DRY configuration ([9aae495](https://github.com/loonghao/dcc-mcp-maya/commit/9aae495516f3e5583772dbbcc735f25405eaa5ae))
* **skills:** add inputSchema to high-impact tools ([#149](https://github.com/loonghao/dcc-mcp-maya/issues/149)) ([963cf6d](https://github.com/loonghao/dcc-mcp-maya/commit/963cf6dc313d5c810bac0b245fae5582963f2991))
* **skills:** add Maya introspect provider + OpenMaya per-version index ([#117](https://github.com/loonghao/dcc-mcp-maya/issues/117), [#115](https://github.com/loonghao/dcc-mcp-maya/issues/115)) ([c61ca52](https://github.com/loonghao/dcc-mcp-maya/commit/c61ca52822314c88106fda6d0acac60541216370))
* **skills:** add maya-annotation, maya-audio, maya-cache, maya-color-grading, maya-constraints-advanced skills ([766a058](https://github.com/loonghao/dcc-mcp-maya/commit/766a058aac8472e2cb5d2def0379ab22dcf8f1f4))
* **skills:** add maya-blend-shape-utils, maya-xform-utils, maya-spline-ik, maya-gpu-cache, maya-instancer skills ([9666097](https://github.com/loonghao/dcc-mcp-maya/commit/9666097a1021199bde7729aa236c1dce8f8d5efc))
* **skills:** add maya-expressions scripts, maya-mocap, maya-muscle, maya-scene-assembly, maya-proxy-mesh skills ([48102c5](https://github.com/loonghao/dcc-mcp-maya/commit/48102c534be06535b03876fd866d5e1a7f222614))
* **skills:** add maya-fluid, maya-ocean, maya-cloth-sim, maya-grooming, maya-export-preset skills ([25971e2](https://github.com/loonghao/dcc-mcp-maya/commit/25971e201ffc5d08901b83ee905c5064b93cf19e))
* **skills:** add maya-paint-effects, maya-hdri, maya-camera-sequence, maya-namespaces, maya-texture-bake skills ([4b5bbee](https://github.com/loonghao/dcc-mcp-maya/commit/4b5bbee1294a1a46218fb592bbaca7bbb2794ddb))
* **skills:** add maya-scripting, maya-utility, maya-pipeline skills ([1da44ae](https://github.com/loonghao/dcc-mcp-maya/commit/1da44ae1f52dd1f14d9bb4b3406d808f1605f384))
* **skills:** add maya-shot-export, maya-material-library, maya-toon, maya-nparticles, maya-render-farm skills ([5e8920a](https://github.com/loonghao/dcc-mcp-maya/commit/5e8920a5e2a8a465faebe5ad3a789571d687550e))
* **skills:** add maya-skinning-utils, maya-rig-utils, maya-render-passes, maya-pose-library, maya-light-rig skills ([afb86a8](https://github.com/loonghao/dcc-mcp-maya/commit/afb86a8fbf645b6cc081459217db15f0cf83e212))
* **skills:** add mtoa plugin availability guards to all 5 maya-arnold-aov scripts; add test_skills_round43 (28 tests) ([c2bc336](https://github.com/loonghao/dcc-mcp-maya/commit/c2bc336b069355accb749031b373ff1aacbba15a))
* **skills:** add ToolAnnotations and SkillGroup to all 64 skills ([e41a1a1](https://github.com/loonghao/dcc-mcp-maya/commit/e41a1a175c72a3dff4959f25b6ab82ee2d8fa4bd))
* **skills:** annotate bundled tools.yaml with execution/affinity ([#84](https://github.com/loonghao/dcc-mcp-maya/issues/84)) ([#91](https://github.com/loonghao/dcc-mcp-maya/issues/91)) ([1b63b82](https://github.com/loonghao/dcc-mcp-maya/commit/1b63b82c42d4fd7f0c76fe41dcc563aa5a91123a))
* **skills:** elevate maya-scripting as primary fall-through entry (bitter-lesson) ([c2a5ac2](https://github.com/loonghao/dcc-mcp-maya/commit/c2a5ac2e6f25cbe15d2057b819e259505a7dc454)), closes [#114](https://github.com/loonghao/dcc-mcp-maya/issues/114)
* **skills:** implement layered skill architecture with explicit routing ([#100](https://github.com/loonghao/dcc-mcp-maya/issues/100)) ([f24f4c7](https://github.com/loonghao/dcc-mcp-maya/commit/f24f4c7e4bc8e4890f8f57e39efc85aeff36663e))
* **skills:** maya-render-farm honours cooperative cancellation ([#85](https://github.com/loonghao/dcc-mcp-maya/issues/85)) ([6d0db98](https://github.com/loonghao/dcc-mcp-maya/commit/6d0db98889e907f46724f51acf581a4f43b09d26))
* **skills:** migrate all 369 skill scripts to dcc_mcp_core.skill API ([fb7a926](https://github.com/loonghao/dcc-mcp-maya/commit/fb7a92600190cf601935f58e0aa07e63a9f8b6e3))
* **skills:** restore 10 bundled skills for mayapy E2E coverage ([#180](https://github.com/loonghao/dcc-mcp-maya/issues/180)) ([253280c](https://github.com/loonghao/dcc-mcp-maya/commit/253280cf46ddde9556e798e70add51fc480e02b1))
* **skills:** Skills SOP — 179+ Maya MCP actions, E2E coverage, multi-instance tests ([f211cbd](https://github.com/loonghao/dcc-mcp-maya/commit/f211cbdbe0ada022866d766ead2fa465bd3a7b8d))


### Bug Fixes

* Add mayapy availability check and lint fixes for CI ([21089e9](https://github.com/loonghao/dcc-mcp-maya/commit/21089e9bb9d78dd0ceadf2c2704b4a8478e3300c))
* align maya CI with core 0.15.9 ([27707ac](https://github.com/loonghao/dcc-mcp-maya/commit/27707ac067f0c5eab8be05ec2a9e079235170be8))
* align MayaMcpServer with DccServerBase 0.15.9 ([783dacc](https://github.com/loonghao/dcc-mcp-maya/commit/783daccc6fa090f77f4c20a24e4e5ae30cf23f72))
* align with dcc-mcp-core 0.14.13 API (find_skills -&gt; search_skills) ([185e164](https://github.com/loonghao/dcc-mcp-maya/commit/185e16412fed9c9b07c7bdde53a9853623ab2135))
* **annotation:** use hasattr check for standalone cmds.annotate detection ([9d6b89a](https://github.com/loonghao/dcc-mcp-maya/commit/9d6b89a833d5eb61240df64d66ad108271178d7c))
* Apply ruff format to resolve formatting issues ([2d43a7e](https://github.com/loonghao/dcc-mcp-maya/commit/2d43a7e5bcd658a3647d4da67f15aacbf7a9d445))
* **ci:** exclude integration tests from standard CI run ([3eb3f20](https://github.com/loonghao/dcc-mcp-maya/commit/3eb3f200548976b94e4633600930e2ff013f9db2))
* **ci:** exclude packaging marker from default test run and fix lint issues ([e08012b](https://github.com/loonghao/dcc-mcp-maya/commit/e08012b635849e96ea4cd76e5c74c64acde416a3))
* **ci:** fix e2e PYTHONPATH expansion and narrow test collection ([dec6763](https://github.com/loonghao/dcc-mcp-maya/commit/dec6763fcb1c14d53263aa75db23d52909ec8340))
* **ci:** fix ruff I001 import order and annotator idempotency ([10b97bb](https://github.com/loonghao/dcc-mcp-maya/commit/10b97bb7bd393ea3c9f9c9c8661c026364eada38))
* **ci:** fix SSL certificate failure in assemble step on Maya 2022/2023 ([46fd348](https://github.com/loonghao/dcc-mcp-maya/commit/46fd3482b60e591aa43d43000dfda1d4d2d76b78))
* **ci:** format diagnostics.py and fix test_start_server assertion ([a2e3c54](https://github.com/loonghao/dcc-mcp-maya/commit/a2e3c54b4a3fe9d6f3cee1c39dd3d68272fa4e99))
* **ci:** install pytest deps into mayapy before running e2e tests ([404df33](https://github.com/loonghao/dcc-mcp-maya/commit/404df332ce5ad42bccfe7e663e16508dda595241))
* **ci:** require Python 3.8+ for dcc-mcp-core 0.17.3 and stub _config in tests ([8fbb44c](https://github.com/loonghao/dcc-mcp-maya/commit/8fbb44c8bf3cfa99a2f4452172898be9fa294451))
* **ci:** update e2e.yml for new assemble output paths ([9567833](https://github.com/loonghao/dcc-mcp-maya/commit/956783310cd0c0c132a0b00783025e022f0ce7e5))
* **ci:** use ubuntu-22.04 for Python 3.7 (ubuntu-latest is 24.04, dropped 3.7) ([#12](https://github.com/loonghao/dcc-mcp-maya/issues/12)) ([ccda505](https://github.com/loonghao/dcc-mcp-maya/commit/ccda505d4fb21a08260cbdc7e36a409fcd70e3b3))
* **deps:** bump dcc-mcp-core to 0.14.19 for three-tier gateway election ([#143](https://github.com/loonghao/dcc-mcp-maya/issues/143)) ([3a78593](https://github.com/loonghao/dcc-mcp-maya/commit/3a78593bedbc31c72702919d4ae105603e43aee6))
* **deps:** bump dcc-mcp-core to 0.14.19 for three-tier gateway election ([#143](https://github.com/loonghao/dcc-mcp-maya/issues/143)) ([23387e0](https://github.com/loonghao/dcc-mcp-maya/commit/23387e09f5b46938c14845fcd409504225f175bb))
* **docs:** validate VitePress build on PRs ([#234](https://github.com/loonghao/dcc-mcp-maya/issues/234)) ([8645a56](https://github.com/loonghao/dcc-mcp-maya/commit/8645a5693d2bdf30399de700f39375466bd3fd82))
* **e2e:** exclude packaging marker from unit test step in e2e workflow ([f558bd3](https://github.com/loonghao/dcc-mcp-maya/commit/f558bd35a938c41a7085aecbc61319f916d5147e))
* **e2e:** fix annotation, metadata, script node and Python 3.7 test failures ([ac46ac4](https://github.com/loonghao/dcc-mcp-maya/commit/ac46ac447b96488a4ec58068a4d3ee9f69ce2079))
* **e2e:** fix deformer E2E tests and mark HTTP tool-call tests as xfail ([592be22](https://github.com/loonghao/dcc-mcp-maya/commit/592be2284471bf5f8a570d468b293b250210bb23))
* **e2e:** lazy-import requests in GatewayTestClient to fix E2E conftest loading ([d913259](https://github.com/loonghao/dcc-mcp-maya/commit/d91325975b70e42f462f4959bc775f2d17e146e3))
* **e2e:** resolve all e2e test failures ([eff4f31](https://github.com/loonghao/dcc-mcp-maya/commit/eff4f31d20ea81ae4f1a1e7ac73797ecfc683f7a))
* ensure Python 3.7+ compatibility across all source files ([#10](https://github.com/loonghao/dcc-mcp-maya/issues/10)) ([8952145](https://github.com/loonghao/dcc-mcp-maya/commit/8952145390a381ad677250cf84dc5f5350048937))
* exclude __skill__*/__group__* stubs from tools/list (issue [#174](https://github.com/loonghao/dcc-mcp-maya/issues/174)) ([#185](https://github.com/loonghao/dcc-mcp-maya/issues/185)) ([05e1d6a](https://github.com/loonghao/dcc-mcp-maya/commit/05e1d6ae3f4a52b254d19fac155149ac93fb5490))
* **execute_python:** default MayaOutputCapture to no-op; opt-in via env var ([b62a7b1](https://github.com/loonghao/dcc-mcp-maya/commit/b62a7b1684fddd9fa4e4b969227953541043964d))
* **executor:** honor tools.yaml affinity: any at runtime ([#168](https://github.com/loonghao/dcc-mcp-maya/issues/168)) ([f17ea96](https://github.com/loonghao/dcc-mcp-maya/commit/f17ea96287d1a10436060f43542fe43747cc3c1c))
* **executor:** replace catalog.set_in_process_executor with register_handler for core 0.14.14 ([a829f74](https://github.com/loonghao/dcc-mcp-maya/commit/a829f748a987bab4227790c519a55bdb04182300)), closes [#122](https://github.com/loonghao/dcc-mcp-maya/issues/122)
* **executor:** wrap dispatcher errors + pass DeferredToolResult through ([#151](https://github.com/loonghao/dcc-mcp-maya/issues/151), [#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([9eef36b](https://github.com/loonghao/dcc-mcp-maya/commit/9eef36b61bb8214c57bcadb526ec8266984189a9))
* harden ci compatibility tests ([392d77c](https://github.com/loonghao/dcc-mcp-maya/commit/392d77c97b293b3d7728843ddcc605c112d5f806))
* harden Maya plugin threading and execute_python ([3ef789a](https://github.com/loonghao/dcc-mcp-maya/commit/3ef789a6f4cade4d44ecc5c5221fbcfa276ab671)), closes [#211](https://github.com/loonghao/dcc-mcp-maya/issues/211) [#212](https://github.com/loonghao/dcc-mcp-maya/issues/212) [#213](https://github.com/loonghao/dcc-mcp-maya/issues/213) [#214](https://github.com/loonghao/dcc-mcp-maya/issues/214) [#215](https://github.com/loonghao/dcc-mcp-maya/issues/215) [#216](https://github.com/loonghao/dcc-mcp-maya/issues/216) [#217](https://github.com/loonghao/dcc-mcp-maya/issues/217) [#218](https://github.com/loonghao/dcc-mcp-maya/issues/218)
* **lint:** remove unused call import and fix import order in test_skills_round46 ([186d4f1](https://github.com/loonghao/dcc-mcp-maya/commit/186d4f12e276b703af3474f091a9585d0b94293d))
* make get_maya_version_string thread-safe with caching ([cac7828](https://github.com/loonghao/dcc-mcp-maya/commit/cac782846dd7c0f428dbd65e23487cc1b1fc1b1e))
* make get_maya_version_string thread-safe without breaking unit tests ([84de7fd](https://github.com/loonghao/dcc-mcp-maya/commit/84de7fd9a039ebf82871a5b326cbf79302fde0aa))
* **maya:** commandPort hygiene and timeout_hint_secs in dispatcher ([#249](https://github.com/loonghao/dcc-mcp-maya/issues/249)) ([c866f8a](https://github.com/loonghao/dcc-mcp-maya/commit/c866f8aa6cf6368da06d1d57b98bfcaf88434ccf))
* **maya:** delegate gateway election to sidecar when SIDECAR=1 ([24639e4](https://github.com/loonghao/dcc-mcp-maya/commit/24639e4b295794a25a7b6b153b567752682bbf88))
* **packaging:** add README.txt fallback in assemble_mod when file not in git checkout ([cf61cc0](https://github.com/loonghao/dcc-mcp-maya/commit/cf61cc055b2a1e4ccec7050bcc13a488a9c677f1))
* **packaging:** add README.txt to git tracking (was excluded by *.txt in .gitignore) ([a90ac8e](https://github.com/loonghao/dcc-mcp-maya/commit/a90ac8e2dd6633703fc80d68e4b16d208cca25f2))
* **packaging:** ensure packaged .mod module works in Maya standalone/batch mode ([b36f689](https://github.com/loonghao/dcc-mcp-maya/commit/b36f689eab0c07750124dce96501d21455e17921))
* **packaging:** replace pip download with PyPI JSON API for cross-platform wheel retrieval ([9331ca3](https://github.com/loonghao/dcc-mcp-maya/commit/9331ca3e2d6e5c91c14aeccd46d250a25254914e))
* **packaging:** replace pip download with PyPI JSON API for cross-platform wheel retrieval ([85ca7c8](https://github.com/loonghao/dcc-mcp-maya/commit/85ca7c83e0c358f5b18fd84a93646a915f308a09))
* **plugin:** defer startup via evalDeferred when autoloaded in interactive Maya ([7653020](https://github.com/loonghao/dcc-mcp-maya/commit/765302045e3a97fda83ceb5c103f08df5c033187))
* **plugin:** disable Maya AutoSave for the duration of MCP session ([9d7b836](https://github.com/loonghao/dcc-mcp-maya/commit/9d7b836c6490f90f00585777d679d41074488124))
* **plugin:** export DCC_MCP_PYTHON_EXECUTABLE / init snippet before server start ([2f57c4e](https://github.com/loonghao/dcc-mcp-maya/commit/2f57c4ea124a9054f6b071abaebdf826cb5b6d05)), closes [#63](https://github.com/loonghao/dcc-mcp-maya/issues/63)
* **plugin:** guard sidecar spawn when handle still set ([e842703](https://github.com/loonghao/dcc-mcp-maya/commit/e8427031444704d4711f9229ca35ac915429c8f1))
* **plugin:** OpenAPI docs uses instance URL, Admin uses gateway URL ([db93dc3](https://github.com/loonghao/dcc-mcp-maya/commit/db93dc3e5d38703056bb34fb74bdd03444e01a87))
* **plugin:** robust cleanup in uninitializePlugin + stale instance warning ([#130](https://github.com/loonghao/dcc-mcp-maya/issues/130)) ([d993e11](https://github.com/loonghao/dcc-mcp-maya/commit/d993e1126dafbf1b44224858137e1d782de2c507))
* **plugin:** stop sidecar on Restart MCP Server ([7bc41f2](https://github.com/loonghao/dcc-mcp-maya/commit/7bc41f2aa325935d6389486ecce41a8f39786ea2))
* **plugin:** suppress commandPort security warning at startup ([#148](https://github.com/loonghao/dcc-mcp-maya/issues/148)) ([14375aa](https://github.com/loonghao/dcc-mcp-maya/commit/14375aad9dd462d56779e0610815b387b710f022))
* **plugin:** unify sidecar + in-process FileRegistry directory (split-brain gateway election) ([2a916eb](https://github.com/loonghao/dcc-mcp-maya/commit/2a916eba67a231566f3b231c80024dc0483b5eeb))
* **plugin:** use gateway URL for OpenAPI docs and Admin panel ([16b1f21](https://github.com/loonghao/dcc-mcp-maya/commit/16b1f21f2090cdc1fd6ec79dd345388cb4ce99aa))
* **plugin:** use maya.api.OpenMaya (API 2.0) to resolve MFnPlugin AttributeError ([4653cd3](https://github.com/loonghao/dcc-mcp-maya/commit/4653cd3c7e776ba0d6d4782ab4fe13e4786bcd4e))
* prune Maya log files on startup ([#207](https://github.com/loonghao/dcc-mcp-maya/issues/207)) ([d8d621b](https://github.com/loonghao/dcc-mcp-maya/commit/d8d621b36a64b7cc72b0902ac88bb1d373c5fa60))
* **pyexec:** auto-correct DCC_MCP_PYTHON_EXECUTABLE when set to a GUI binary ([#129](https://github.com/loonghao/dcc-mcp-maya/issues/129)) ([ae1c74f](https://github.com/loonghao/dcc-mcp-maya/commit/ae1c74f9625cb92ff98c14ce0e262e0217442b18))
* **release:** add workflow_dispatch input for manual build-mod; fix Python 3.14-&gt;3.12 ([69c10d1](https://github.com/loonghao/dcc-mcp-maya/commit/69c10d1befc4b79caf0d868e9331cf43ed7de1f8))
* **release:** use inputs.tag_name as fallback for version/tag in manual workflow dispatch ([60cea92](https://github.com/loonghao/dcc-mcp-maya/commit/60cea920710d50dfd5f0d7fae9e848ebede842a3))
* **release:** use PERSONAL_ACCESS_TOKEN for release-please PR creation ([#16](https://github.com/loonghao/dcc-mcp-maya/issues/16)) ([ed795a8](https://github.com/loonghao/dcc-mcp-maya/commit/ed795a8608539111e69c1a0d5c7959eddef8598a))
* Remove unused imports and blank line whitespace ([4b7e6ef](https://github.com/loonghao/dcc-mcp-maya/commit/4b7e6eff83322fff3cf1ad98b543137e7e3688f1))
* **render:** capture_viewport falls back to off-screen render ([#152](https://github.com/loonghao/dcc-mcp-maya/issues/152)) ([a7191c1](https://github.com/loonghao/dcc-mcp-maya/commit/a7191c1323f8d9ca5983842b554f69e4266c4ccd))
* resolve CI failures and clean up repo ([eb68c2d](https://github.com/loonghao/dcc-mcp-maya/commit/eb68c2da7fce5ca879cbe5daa6bae4ea807083e0))
* resolve ci failures for core 0.17.6 ([0b1e34f](https://github.com/loonghao/dcc-mcp-maya/commit/0b1e34fd23b094b4123d397b53742955a5c38891))
* resolve F401 lint errors in __init__.py and _skill_loader.py ([13fcbf8](https://github.com/loonghao/dcc-mcp-maya/commit/13fcbf8aa44a620f4649bf8966cf1c7987ea338e))
* **safe-session:** remove cmds.* dialog monkey-patch (crashes Maya on file new / Arnold) ([3b88ee7](https://github.com/loonghao/dcc-mcp-maya/commit/3b88ee77be0ab2dccf34175110e0b2ab2daa3004))
* **scripting:** cooperative defer cancellation + native stdout capture ([#151](https://github.com/loonghao/dcc-mcp-maya/issues/151), [#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([fb04a8f](https://github.com/loonghao/dcc-mcp-maya/commit/fb04a8f44e3aa9d995ff62b5bc00579a75f6e492))
* **scripting:** wire minimal skill handlers after load ([cf94be7](https://github.com/loonghao/dcc-mcp-maya/commit/cf94be7a0a0db1cb888eb543e96caff02ddb5f99))
* serialize mayapy standalone dispatch ([1ebabec](https://github.com/loonghao/dcc-mcp-maya/commit/1ebabec7f51bead3d9814a978a5875f46e07491b))
* serialize standalone maya dispatch globally ([8dd10cd](https://github.com/loonghao/dcc-mcp-maya/commit/8dd10cd1b5022f26bb038e8f70eb53b59e65870d))
* **server:** clear job_storage_path when empty string disables persistence ([178df6c](https://github.com/loonghao/dcc-mcp-maya/commit/178df6cce8370ab7436dea1c463e062392cf29d7))
* **server:** correctly call main(**params) in in-process executor ([#108](https://github.com/loonghao/dcc-mcp-maya/issues/108)) ([6f50992](https://github.com/loonghao/dcc-mcp-maya/commit/6f5099211708c57db2e0b30a66f1eccd5e432be1))
* **server:** pass DccServerOptions with options= keyword ([6f6f3a9](https://github.com/loonghao/dcc-mcp-maya/commit/6f6f3a9930087d911036268342c3acb5fce871e2))
* **server:** restore module-level _server_instance for plugin compatibility ([3a618dd](https://github.com/loonghao/dcc-mcp-maya/commit/3a618dd58d133f111291a8eabe6f3e250f459b52))
* **server:** wire in-process executor on dispatcher attach ([#142](https://github.com/loonghao/dcc-mcp-maya/issues/142)) ([597793f](https://github.com/loonghao/dcc-mcp-maya/commit/597793f0304950ac81884976785d5a98ee815d47))
* **server:** wire in-process executor on dispatcher attach ([#142](https://github.com/loonghao/dcc-mcp-maya/issues/142)) ([d66f1b4](https://github.com/loonghao/dcc-mcp-maya/commit/d66f1b49e15afffd363abe54b19137b359458583))
* set non-core tool groups to default_active: false for progressive exposure ([82d1c0f](https://github.com/loonghao/dcc-mcp-maya/commit/82d1c0f4c094b3ee5460b21a86d43986cfe68180))
* **sidecar:** route qtserver dispatch through execute_in_process so affinity is respected ([9856983](https://github.com/loonghao/dcc-mcp-maya/commit/9856983a5a1ddc41146fe886afabfaf6e4260aa7))
* **skills:** deduplicate bundled skill ownership ([#232](https://github.com/loonghao/dcc-mcp-maya/issues/232)) ([dcb4cda](https://github.com/loonghao/dcc-mcp-maya/commit/dcb4cda7e5fa9b3d9fbc8bbdae03d00b9031bee9))
* **skills:** normalize execute_python/execute_mel params + capture stdout ([#150](https://github.com/loonghao/dcc-mcp-maya/issues/150), [#151](https://github.com/loonghao/dcc-mcp-maya/issues/151), [#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([4c0eb7e](https://github.com/loonghao/dcc-mcp-maya/commit/4c0eb7e00717e0b3074305ceb11cafb4f1fd62f8))
* Skip get_capabilities tests until method is implemented ([fb4e626](https://github.com/loonghao/dcc-mcp-maya/commit/fb4e6264f3a97a00157d038b902df4434ae9b1dc))
* Skip test_skills_round44 when DccCapabilities unavailable ([c743c6c](https://github.com/loonghao/dcc-mcp-maya/commit/c743c6cedacc23d93e5a81c563a80fcc88573cb1))
* skip unsafe mayapy shutdown hook ([40a8a56](https://github.com/loonghao/dcc-mcp-maya/commit/40a8a56745e24698082af37d00bdfd9ee33b163f))
* stabilize ci with core 0.17.6 ([da1a7b6](https://github.com/loonghao/dcc-mcp-maya/commit/da1a7b68a6bd837267925e8f1a94ad98381f7c12))
* stabilize Maya CI against dcc-mcp-core 0.15.9 ([9a5b575](https://github.com/loonghao/dcc-mcp-maya/commit/9a5b57564d6ccb6c9fd3adcd02a6a6f4c600cff9))
* stabilize Maya MCP execution and discovery ([2e95e37](https://github.com/loonghao/dcc-mcp-maya/commit/2e95e372539f2e7d54b5ef749ad167b5cb9d62f7))
* stabilize Maya standalone E2E on core 0.15.9 ([9459c6e](https://github.com/loonghao/dcc-mcp-maya/commit/9459c6e8e617538ae5300094ef855c7b0b798cb0))
* stabilize mayapy ci execution ([6cb4c79](https://github.com/loonghao/dcc-mcp-maya/commit/6cb4c79cbc94dd0ebcfaeafbe1b5ef476302d425))
* support core dispatch in standalone maya ([59e5d69](https://github.com/loonghao/dcc-mcp-maya/commit/59e5d69bb4d65bd3b77ff3e5d4c4d0f0232eb3a8))
* **test:** force ImportError in test_with_maya_import_error via patch.dict ([05d0278](https://github.com/loonghao/dcc-mcp-maya/commit/05d02785b69bb0c9fd7796ce8b330db39d7704b3))
* **tests:** fix Python 3.7 compat and lint in test_skills_round45 ([e88d0f4](https://github.com/loonghao/dcc-mcp-maya/commit/e88d0f4a5ae87d842b77b3dbc3cd71095c780b41))
* **tests:** make search_skills mock assertions Python 3.7 compatible ([d197ece](https://github.com/loonghao/dcc-mcp-maya/commit/d197ecede363906a3aa01c4e7e7efaf2029a3688))
* **tests:** relax maya-scene tool assertion for progressive loading ([#71](https://github.com/loonghao/dcc-mcp-maya/issues/71)) ([d044ee8](https://github.com/loonghao/dcc-mcp-maya/commit/d044ee8a8eb61a3556fcce066a4dc869a1695eca))
* **tests:** relax tool assertions for progressive skill loading ([#77](https://github.com/loonghao/dcc-mcp-maya/issues/77)) ([0e773ef](https://github.com/loonghao/dcc-mcp-maya/commit/0e773ef5ef5ff444d105f4a8235ca086bdcd34be))
* **tests:** update E2E assertions for bare tool names (dcc-mcp-core 0.14.1+) ([ea5ff30](https://github.com/loonghao/dcc-mcp-maya/commit/ea5ff30a089df50acf406bbd30adc863809fdbb3))
* **tests:** use tuple indexing for mock.call kwargs on Python 3.7 ([4152a20](https://github.com/loonghao/dcc-mcp-maya/commit/4152a204e5ccd3a103385603dfb76e6eca70de3a))
* **test:** update e2e test for progressive skill/group loading ([17f41c8](https://github.com/loonghao/dcc-mcp-maya/commit/17f41c816e4e9bd3aa6a7809e744696950884ef6))
* **test:** update E2E tool name assertions for core 0.13+ naming convention ([dbf54fb](https://github.com/loonghao/dcc-mcp-maya/commit/dbf54fb93b508c333649a3aebb994208f4a84e9b))
* **test:** update test_skills_round34 for ToolAnnotations/SkillGroup SKILL.md format ([04be232](https://github.com/loonghao/dcc-mcp-maya/commit/04be2320bf1f9dc0bddd6e292ab8ceb0479b7423))
* **test:** update tool name assertions for core 0.13+ naming convention ([e4ed560](https://github.com/loonghao/dcc-mcp-maya/commit/e4ed560bb92752f5c5ff64df7ed2805cb9ca7eb0))
* **test:** use correct param name for activate_tool_group ([18c8ddb](https://github.com/loonghao/dcc-mcp-maya/commit/18c8ddb89dc28dd69b07851df131502bfbfad049))
* update justfile to use create_skill_server (renamed in core 0.13+) ([#74](https://github.com/loonghao/dcc-mcp-maya/issues/74)) ([13eb584](https://github.com/loonghao/dcc-mcp-maya/commit/13eb584159f21f168445e4c27b859cee7b59824c))
* Upgrade upload-artifact to v4 ([43dc989](https://github.com/loonghao/dcc-mcp-maya/commit/43dc98939397321423462c56dec232fc03c3d498))
* **version-probe:** avoid cmds.about off main thread ([a15839f](https://github.com/loonghao/dcc-mcp-maya/commit/a15839f40b8a96537f7313daeadd08a70fe09866))


### Code Refactoring

* align Maya adapter with core contracts ([56e520c](https://github.com/loonghao/dcc-mcp-maya/commit/56e520cbf7d3a82ab3ddb6200cd5c30d1ac8eeac))
* align with dcc-mcp-core 0.13 API ([11b2e54](https://github.com/loonghao/dcc-mcp-maya/commit/11b2e54e641dc45242cffb5ac3afb051419862d8))
* **api:** fix Python 3.7 type annotations; refactor 14 skill scripts to use validate_node_exists/batch_validate_nodes; add test_skills_round26 (61 tests) ([f566c19](https://github.com/loonghao/dcc-mcp-maya/commit/f566c19d1945101bcc32d7144d001ac186fb5ec2))
* **api:** replace hand-written objExists guards with validate_node_exists/batch_validate_nodes in maya-attributes, maya-scene, maya-uv-ops, maya-constraints, maya-materials (34 files, 36 objExists removed); add test_skills_round27 (42 tests) ([6eacdee](https://github.com/loonghao/dcc-mcp-maya/commit/6eacdeee65a0ee8012ce3d0230206d833e948805))
* **dispatcher:** adopt core HostUiDispatcherBase for Maya UI thread ([b7e4aa5](https://github.com/loonghao/dcc-mcp-maya/commit/b7e4aa5e75a56b8f7578866851f1fa749489e998))
* **dispatcher:** split dispatcher.py into a dispatcher/ directory module ([#131](https://github.com/loonghao/dcc-mcp-maya/issues/131)) ([a2d6c7c](https://github.com/loonghao/dcc-mcp-maya/commit/a2d6c7c398011b36f30f7e401b07b60b71c57540))
* narrow typed output exception handling ([6ffdd21](https://github.com/loonghao/dcc-mcp-maya/commit/6ffdd21065a120f27409f36df0558a5a628350b9))
* **packaging:** generate .mod file at install time from module-info.json ([333a665](https://github.com/loonghao/dcc-mcp-maya/commit/333a665297ec61d00530ef29f24d3ad57d828738))
* **packaging:** rewrite install scripts and add portable/pipeline ZIP variants ([c01cda5](https://github.com/loonghao/dcc-mcp-maya/commit/c01cda55444ebd59cdcf17bb5e97e9e70b310ab9))
* **plugin:** add maya_useNewAPI(); simplify to direct API 2.0 import ([30204b8](https://github.com/loonghao/dcc-mcp-maya/commit/30204b8b42b650dc2019e847448be3ed170fe280))
* reduce bundled skills from 64 to 12 core pipeline skills ([2c57f0d](https://github.com/loonghao/dcc-mcp-maya/commit/2c57f0d212140f6fff23a228d6fd1660e4308763))
* remove legacy gateway toggles and align scripting surface ([4933a04](https://github.com/loonghao/dcc-mcp-maya/commit/4933a041d5e3b208fd402d2200c9eac9285f5f69))
* **safe-session:** remove _safe_session module entirely ([c9bfb5c](https://github.com/loonghao/dcc-mcp-maya/commit/c9bfb5c41c53e880e0b3c8ee8f26a173eb6d4a41))
* **server:** migrate to create_skill_manager API + remove dead executor code ([#23](https://github.com/loonghao/dcc-mcp-maya/issues/23)) ([f0e14da](https://github.com/loonghao/dcc-mcp-maya/commit/f0e14da94d021b5fc0ebb110bf9405a39bd07c4f))
* **server:** split MayaMcpServer per SRP into env / executor / loader / probe / transport modules ([#133](https://github.com/loonghao/dcc-mcp-maya/issues/133)) ([58043dc](https://github.com/loonghao/dcc-mcp-maya/commit/58043dc8a4223e08f9fbc35baf02afe0ace26a11))
* **skills:** bulk migrate 136 scripts from cmds.objExists to validate_node_exists; add test_skills_round29 (25 tests) ([c0a4bab](https://github.com/loonghao/dcc-mcp-maya/commit/c0a4babd00bee1ca115b9353aa9c94ce6a709f95))
* **skills:** migrate 18 cmds.objExists guards to validate_node_exists; add test_skills_round31 (70 tests); fix ruff E741 in test_round30 ([0ca9756](https://github.com/loonghao/dcc-mcp-maya/commit/0ca9756a3a5644549dbc4e0067c47e93e55fe539))
* **skills:** migrate 26 list-comp cmds.objExists to batch_validate_nodes; add test_skills_round32 (76 tests) ([951c3bf](https://github.com/loonghao/dcc-mcp-maya/commit/951c3bfdde3bacb628aaaafa114fc512e8c29066))
* **skills:** migrate 44 cmds.objExists guards to validate_node_exists/batch_validate_nodes; add test_skills_round30 (36 tests) ([0b665cd](https://github.com/loonghao/dcc-mcp-maya/commit/0b665cdd265ff05fdf0ec83c8689b2634320ab6f))
* **skills:** migrate all 369 skill scripts to dcc_mcp_maya.api ([c4a4552](https://github.com/loonghao/dcc-mcp-maya/commit/c4a4552dd1d55c4a85d9616064b0f90001eaeeb3))
* **skills:** migrate all skills to sibling-file pattern (dcc-mcp-core [#356](https://github.com/loonghao/dcc-mcp-maya/issues/356)) ([#90](https://github.com/loonghao/dcc-mcp-maya/issues/90)) ([2598538](https://github.com/loonghao/dcc-mcp-maya/commit/259853848cfb71aa17261aa01e83b43dfabef6c2))
* **skills:** migrate maya-mash, maya-selection, maya-xgen 15 scripts to skill_entry style; update test_skills_round13 for new API; add test_skills_round28 (49 tests) ([d494184](https://github.com/loonghao/dcc-mcp-maya/commit/d494184e7591622612e0a8d6d569f4526c5049bb))
* split Maya registration into phases ([#208](https://github.com/loonghao/dcc-mcp-maya/issues/208)) ([ac686c0](https://github.com/loonghao/dcc-mcp-maya/commit/ac686c09783b3d5066d0946efba60c410f50bf94))
* split standalone e2e scenarios ([fda8c59](https://github.com/loonghao/dcc-mcp-maya/commit/fda8c59495c6428985c1f3fbf0e34237f81b825a))
* **test:** split progressive-loading test into two focused tests ([8483640](https://github.com/loonghao/dcc-mcp-maya/commit/8483640da4d1382c01db2c8c872ac8d736bd3a20))
* use DccServerBase from dcc-mcp-core ([#54](https://github.com/loonghao/dcc-mcp-maya/issues/54)) ([906779d](https://github.com/loonghao/dcc-mcp-maya/commit/906779d84d931755dd7838e236d8f2348e3df6b1))


### Documentation

* add AI-friendly documentation and fix VitePress navigation ([a3c7ac0](https://github.com/loonghao/dcc-mcp-maya/commit/a3c7ac0701ee6bbd0097567e1a960563dca43a6c))
* **advanced:** document defer=True long-running script workflow ([#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([927471c](https://github.com/loonghao/dcc-mcp-maya/commit/927471c0819fbe0d866fb8b24d37fc34f70a390e))
* **agents:** link upstream dcc-mcp-core llms.txt as authoritative API reference ([#134](https://github.com/loonghao/dcc-mcp-maya/issues/134)) ([6f285ee](https://github.com/loonghao/dcc-mcp-maya/commit/6f285eebc32c3f13bdace24eaf638b3d2b4297a3))
* document bundled skills, IPC diagnostics, and include_bundled param ([ce01865](https://github.com/loonghao/dcc-mcp-maya/commit/ce018656d5a5950f7e88c1af02a655619bf7138c))
* **env:** document DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST ([#238](https://github.com/loonghao/dcc-mcp-maya/issues/238)) ([48af9ea](https://github.com/loonghao/dcc-mcp-maya/commit/48af9ea904b60e082bf0aeb04a8639c32f2ae665))
* fix core dependency version inconsistency ([633a9be](https://github.com/loonghao/dcc-mcp-maya/commit/633a9be7413bc83c6aa993698ebee96a79d7cd84))
* fix core dependency version inconsistency in llms.txt and llms-full.txt ([9f39a09](https://github.com/loonghao/dcc-mcp-maya/commit/9f39a0978dca92760bb7b090544b0ab6c8135c46))
* fix tool/skill count errors and add README_zh.md ([6bcca3f](https://github.com/loonghao/dcc-mcp-maya/commit/6bcca3f15a407647cb33b32d2d5cc08652da570a))
* fix tool/skill count errors and add README_zh.md ([33c609c](https://github.com/loonghao/dcc-mcp-maya/commit/33c609cf7294a86299b293243ed15e23d737e645))
* fix VitePress AGENTS links ([09e3021](https://github.com/loonghao/dcc-mcp-maya/commit/09e3021801e0ab10b0b939fd6d6d9650162c3711))
* **maya:** P0-P2 token path, FBX contract, bulk workflow ([be1ca96](https://github.com/loonghao/dcc-mcp-maya/commit/be1ca96d4105c1b6951bc00403a1ccb4afde05f0))
* multi-Maya-instance deployment on a single workstation ([#88](https://github.com/loonghao/dcc-mcp-maya/issues/88)) ([#92](https://github.com/loonghao/dcc-mcp-maya/issues/92)) ([297aa02](https://github.com/loonghao/dcc-mcp-maya/commit/297aa029df57a1ce05ebb8356df1a2aa720f385d))
* point AGENTS to upstream VRS gateway replay traces ([b1c5bba](https://github.com/loonghao/dcc-mcp-maya/commit/b1c5bba6e5712b8129f60809e5a639f2730b5892))
* point AGENTS to upstream VRS gateway replay traces ([944cd70](https://github.com/loonghao/dcc-mcp-maya/commit/944cd701e8143775ddc5d226483e9dc7b15d9888))
* remove stale skill_executor references; fix plugin path in AGENTS ([48ef104](https://github.com/loonghao/dcc-mcp-maya/commit/48ef10462e54a07d4e9dc70da167c44f280464e5))
* **skills:** warn about rigidBody dynamics crashes in execute_python ([8e3ebf1](https://github.com/loonghao/dcc-mcp-maya/commit/8e3ebf1937940722e749a4643c3307992100c8d5))
* update docs site with adapter/scene/snapshot API pages and additional guides ([c8d58f6](https://github.com/loonghao/dcc-mcp-maya/commit/c8d58f68dd8697dc0f9a9524877088d3ec112a61))
* update skill count from 64 to 12 packages (73 scripts) ([8896a25](https://github.com/loonghao/dcc-mcp-maya/commit/8896a25edd60e80c6d598a951ca74244b88de710))
* update skill count from 64 to 12 packages (73 scripts) ([#141](https://github.com/loonghao/dcc-mcp-maya/issues/141)) ([0b4c749](https://github.com/loonghao/dcc-mcp-maya/commit/0b4c749e8a1a00066dd9d713c509d2171ed70f69))
* update version to 0.2.20 and add Rust-backed dispatcher documentation ([f7416fc](https://github.com/loonghao/dcc-mcp-maya/commit/f7416fcae2444ec7b6a581bd1a07b3a5b1851954))
* update version to 0.2.20 and add Rust-backed dispatcher documentation ([fcd2303](https://github.com/loonghao/dcc-mcp-maya/commit/fcd23036cdfad7d260cce4d4311772335d714d45))

## [0.2.29](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.28...v0.2.29) (2026-05-14)


### Features

* **plugin:** replace MCP menu items with OpenAPI docs and Admin panel links ([2eafe7a](https://github.com/loonghao/dcc-mcp-maya/commit/2eafe7a7a8eb812ba7173e7d5da01117c93001c0))
* **scripting:** spill long inline execute_python to host temp file ([09645b0](https://github.com/loonghao/dcc-mcp-maya/commit/09645b04f23bd0272999689302adb808a40a5006))


### Bug Fixes

* align maya CI with core 0.15.9 ([06dd328](https://github.com/loonghao/dcc-mcp-maya/commit/06dd3283e55b6e41aa669ae3009f4eba96f4e355))
* align MayaMcpServer with DccServerBase 0.15.9 ([6007ce8](https://github.com/loonghao/dcc-mcp-maya/commit/6007ce89955244c3fe7dbbdf6cff5a6d71495c8d))
* harden Maya plugin threading and execute_python ([6c39aea](https://github.com/loonghao/dcc-mcp-maya/commit/6c39aea1a11cc6c108f142465ac4a4ea26cf46d8)), closes [#211](https://github.com/loonghao/dcc-mcp-maya/issues/211) [#212](https://github.com/loonghao/dcc-mcp-maya/issues/212) [#213](https://github.com/loonghao/dcc-mcp-maya/issues/213) [#214](https://github.com/loonghao/dcc-mcp-maya/issues/214) [#215](https://github.com/loonghao/dcc-mcp-maya/issues/215) [#216](https://github.com/loonghao/dcc-mcp-maya/issues/216) [#217](https://github.com/loonghao/dcc-mcp-maya/issues/217) [#218](https://github.com/loonghao/dcc-mcp-maya/issues/218)
* make get_maya_version_string thread-safe with caching ([1797164](https://github.com/loonghao/dcc-mcp-maya/commit/17971641ec2d992f5b9761e99919b5923c1ec34b))
* make get_maya_version_string thread-safe without breaking unit tests ([3365597](https://github.com/loonghao/dcc-mcp-maya/commit/3365597a79c036788de7adfe68d27e7fd9da9ed6))
* **plugin:** OpenAPI docs uses instance URL, Admin uses gateway URL ([b20d17e](https://github.com/loonghao/dcc-mcp-maya/commit/b20d17e730857557cbb9612fc6a4f38b55041057))
* **plugin:** use gateway URL for OpenAPI docs and Admin panel ([69e08f5](https://github.com/loonghao/dcc-mcp-maya/commit/69e08f56d470fe12f014a2404f3f760f5b5467a8))
* resolve F401 lint errors in __init__.py and _skill_loader.py ([0c0e335](https://github.com/loonghao/dcc-mcp-maya/commit/0c0e335fb5270e760dd414ef46bccbfc05e66041))
* **server:** pass DccServerOptions with options= keyword ([b27bbd4](https://github.com/loonghao/dcc-mcp-maya/commit/b27bbd4a811b3dc1a6b780bf703869a37e4075c3))
* **skills:** deduplicate bundled skill ownership ([#232](https://github.com/loonghao/dcc-mcp-maya/issues/232)) ([1ad8a1a](https://github.com/loonghao/dcc-mcp-maya/commit/1ad8a1a08ac3fc30480a3ceca6c3b3980d94e114))
* stabilize Maya CI against dcc-mcp-core 0.15.9 ([fd0d974](https://github.com/loonghao/dcc-mcp-maya/commit/fd0d9741f0db9a679e4e0d3f426881fcedcf98c9))
* stabilize Maya standalone E2E on core 0.15.9 ([db1908d](https://github.com/loonghao/dcc-mcp-maya/commit/db1908dee4fd8c86abc40af1a4a0eb116b087b22))
* **version-probe:** avoid cmds.about off main thread ([ee57310](https://github.com/loonghao/dcc-mcp-maya/commit/ee57310cb4bc6b3290b89d4672d8df44ad414afe))


### Code Refactoring

* remove legacy gateway toggles and align scripting surface ([3dd1a8a](https://github.com/loonghao/dcc-mcp-maya/commit/3dd1a8abdba9a448608af81929f682e2ebe22e3b))


### Documentation

* **maya:** P0-P2 token path, FBX contract, bulk workflow ([70718d1](https://github.com/loonghao/dcc-mcp-maya/commit/70718d1107eb5430369c191c42908989afe7f8fb))
* point AGENTS to upstream VRS gateway replay traces ([ff676f0](https://github.com/loonghao/dcc-mcp-maya/commit/ff676f032e6cf07b8b173f27d157f3cd73f29cb7))
* point AGENTS to upstream VRS gateway replay traces ([e36076c](https://github.com/loonghao/dcc-mcp-maya/commit/e36076c1593babc5fe98dc9765e30fe28e483d1b))
* **skills:** warn about rigidBody dynamics crashes in execute_python ([9c4f3fc](https://github.com/loonghao/dcc-mcp-maya/commit/9c4f3fcaa7a718af5e12005a227dbf17134744ef))

## [0.2.28](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.27...v0.2.28) (2026-05-12)


### Bug Fixes

* prune Maya log files on startup ([#207](https://github.com/loonghao/dcc-mcp-maya/issues/207)) ([334815c](https://github.com/loonghao/dcc-mcp-maya/commit/334815c64facbabe954ba63bd73bf3df28604fb5))
* stabilize Maya MCP execution and discovery ([6dea24c](https://github.com/loonghao/dcc-mcp-maya/commit/6dea24c81f9e9e0263b8dafcaa7d27233089b2da))


### Code Refactoring

* narrow typed output exception handling ([3cc24f4](https://github.com/loonghao/dcc-mcp-maya/commit/3cc24f40fc06df20056220610037a2902b84e2f2))
* split Maya registration into phases ([#208](https://github.com/loonghao/dcc-mcp-maya/issues/208)) ([0389919](https://github.com/loonghao/dcc-mcp-maya/commit/03899197274523d8f09f1dca4724c3f71b9a79bf))
* split standalone e2e scenarios ([95c2c77](https://github.com/loonghao/dcc-mcp-maya/commit/95c2c772d5ad85c4c76421054c9103a82f8b0f86))

## [0.2.27](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.26...v0.2.27) (2026-05-09)


### Features

* **readiness:** wire three-state ReadinessProbe into MayaMcpServer ([#184](https://github.com/loonghao/dcc-mcp-maya/issues/184)) ([#188](https://github.com/loonghao/dcc-mcp-maya/issues/188)) ([e96541a](https://github.com/loonghao/dcc-mcp-maya/commit/e96541a5626358130fc65b4fd4c4d621fd1c1b66))
* **resources:** wire Maya scene + producers into core 0.15.0 ResourceRegistry ([#187](https://github.com/loonghao/dcc-mcp-maya/issues/187)) ([#190](https://github.com/loonghao/dcc-mcp-maya/issues/190)) ([cf4b4a1](https://github.com/loonghao/dcc-mcp-maya/commit/cf4b4a17c6d5e81ee5feab4535c83e27f2469978))
* **shutdown:** harden plugin for non-cooperative Maya exits ([#186](https://github.com/loonghao/dcc-mcp-maya/issues/186)) ([#189](https://github.com/loonghao/dcc-mcp-maya/issues/189)) ([8c8f94e](https://github.com/loonghao/dcc-mcp-maya/commit/8c8f94e755f811b19feecf777d92cc4b662bfd96))
* **skills:** restore 10 bundled skills for mayapy E2E coverage ([#180](https://github.com/loonghao/dcc-mcp-maya/issues/180)) ([5a70f6e](https://github.com/loonghao/dcc-mcp-maya/commit/5a70f6eed04491f554c53ea7b93e769bd9ffdb7e))


### Bug Fixes

* exclude __skill__*/__group__* stubs from tools/list (issue [#174](https://github.com/loonghao/dcc-mcp-maya/issues/174)) ([#185](https://github.com/loonghao/dcc-mcp-maya/issues/185)) ([8a4bff2](https://github.com/loonghao/dcc-mcp-maya/commit/8a4bff295d2be201316f007d6dc2ab45e43f7418))


### Code Refactoring

* align Maya adapter with core contracts ([8d36e5d](https://github.com/loonghao/dcc-mcp-maya/commit/8d36e5d063b43865e0eb27fecb5c0a6756a097b0))


### Documentation

* fix VitePress AGENTS links ([36198fb](https://github.com/loonghao/dcc-mcp-maya/commit/36198fba91391425915e6248d60e52b8ee01a635))

## [0.2.26](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.25...v0.2.26) (2026-05-03)


### Features

* adopt core host dispatcher for Maya skills ([#177](https://github.com/loonghao/dcc-mcp-maya/issues/177)) ([45ff231](https://github.com/loonghao/dcc-mcp-maya/commit/45ff2310c96d0c7b8a4073610e6fd2de6bbdb851)), closes [#136](https://github.com/loonghao/dcc-mcp-maya/issues/136) [#173](https://github.com/loonghao/dcc-mcp-maya/issues/173) [#176](https://github.com/loonghao/dcc-mcp-maya/issues/176)
* **capability:** publish unloaded skills in capability manifest ([#178](https://github.com/loonghao/dcc-mcp-maya/issues/178)) ([5c82e5e](https://github.com/loonghao/dcc-mcp-maya/commit/5c82e5e6abea891d0bc2192d2875bf4fac3db368)), closes [#174](https://github.com/loonghao/dcc-mcp-maya/issues/174)
* **core-0.14.22:** wire tool_exposure + cursor-safe names, typed output helper ([#172](https://github.com/loonghao/dcc-mcp-maya/issues/172)) ([fb7b60f](https://github.com/loonghao/dcc-mcp-maya/commit/fb7b60f0339165f57ea614086e84f305da1b3990))

## [0.2.25](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.24...v0.2.25) (2026-05-02)


### Features

* **gateway:** compact capability manifest + context snapshot ([#163](https://github.com/loonghao/dcc-mcp-maya/issues/163), [#164](https://github.com/loonghao/dcc-mcp-maya/issues/164), [#165](https://github.com/loonghao/dcc-mcp-maya/issues/165)) ([#166](https://github.com/loonghao/dcc-mcp-maya/issues/166)) ([cec2bed](https://github.com/loonghao/dcc-mcp-maya/commit/cec2bede2e14fb6b33298949df52543d3e8ca80a))
* **project:** wire dcc-mcp-core register_project_tools into MayaMcpServer ([#576](https://github.com/loonghao/dcc-mcp-maya/issues/576)) ([#169](https://github.com/loonghao/dcc-mcp-maya/issues/169)) ([4733b8a](https://github.com/loonghao/dcc-mcp-maya/commit/4733b8a1570179a59486cbd3616130652d267ad9))


### Bug Fixes

* **executor:** honor tools.yaml affinity: any at runtime ([#168](https://github.com/loonghao/dcc-mcp-maya/issues/168)) ([d09d18c](https://github.com/loonghao/dcc-mcp-maya/commit/d09d18c3d1bf6f39a5b4c43ce56a25fd68568dd5))


### Documentation

* fix core dependency version inconsistency ([c0c4f28](https://github.com/loonghao/dcc-mcp-maya/commit/c0c4f2829ffcea4d12132fcb0f835c463959ab34))
* fix core dependency version inconsistency in llms.txt and llms-full.txt ([7cc8237](https://github.com/loonghao/dcc-mcp-maya/commit/7cc82373617c05b136caeca946c6df48b0764ab6))

## [0.2.24](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.23...v0.2.24) (2026-05-01)


### Bug Fixes

* **scripting:** wire minimal skill handlers after load ([7a519c7](https://github.com/loonghao/dcc-mcp-maya/commit/7a519c70db901ba1234334f6b0ba1695379d5224))

## [0.2.23](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.22...v0.2.23) (2026-05-01)


### Bug Fixes

* **scripting:** cooperative defer cancellation + native stdout capture ([#151](https://github.com/loonghao/dcc-mcp-maya/issues/151), [#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([3e1714d](https://github.com/loonghao/dcc-mcp-maya/commit/3e1714d1aa97f7d314eaebe6a490f03049ac12f2))
* **tests:** use tuple indexing for mock.call kwargs on Python 3.7 ([43e41a3](https://github.com/loonghao/dcc-mcp-maya/commit/43e41a30f48a98308d9b70d6bdaa456f2e804fe8))


### Documentation

* **advanced:** document defer=True long-running script workflow ([#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([8230341](https://github.com/loonghao/dcc-mcp-maya/commit/82303412339865a085015bdd0337f5f7f45984c5))

## [0.2.22](https://github.com/loonghao/dcc-mcp-maya/compare/v0.2.21...v0.2.22) (2026-05-01)


### Features

* **server:** DCC_MCP_MAYA_STRICT_SKILL_SCAN + stale-aware discovery ([#144](https://github.com/loonghao/dcc-mcp-maya/issues/144)) ([e51cbf7](https://github.com/loonghao/dcc-mcp-maya/commit/e51cbf7a81c8e334a24e63e8a2d70d18c9ad98a6))
* **server:** wire workflows + job recovery knobs ([#145](https://github.com/loonghao/dcc-mcp-maya/issues/145)) ([335e5c5](https://github.com/loonghao/dcc-mcp-maya/commit/335e5c5e1f1a4fdab7f249ecc0a6bba3b2d34962))
* **skills:** add inputSchema to high-impact tools ([#149](https://github.com/loonghao/dcc-mcp-maya/issues/149)) ([9e27849](https://github.com/loonghao/dcc-mcp-maya/commit/9e27849060b4735bce0e067fe75f56ae0c21b5a6))


### Bug Fixes

* **deps:** bump dcc-mcp-core to 0.14.19 for three-tier gateway election ([#143](https://github.com/loonghao/dcc-mcp-maya/issues/143)) ([efe91e4](https://github.com/loonghao/dcc-mcp-maya/commit/efe91e421d1415fce179b8cc1faeb7f0334d6011))
* **executor:** wrap dispatcher errors + pass DeferredToolResult through ([#151](https://github.com/loonghao/dcc-mcp-maya/issues/151), [#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([0d50c7e](https://github.com/loonghao/dcc-mcp-maya/commit/0d50c7ed37f040ead9ad17e107da730ca8c1ddc4))
* **plugin:** suppress commandPort security warning at startup ([#148](https://github.com/loonghao/dcc-mcp-maya/issues/148)) ([0aa51c3](https://github.com/loonghao/dcc-mcp-maya/commit/0aa51c3445bf95650614e3695eb3af0f0447b39b))
* **render:** capture_viewport falls back to off-screen render ([#152](https://github.com/loonghao/dcc-mcp-maya/issues/152)) ([288b039](https://github.com/loonghao/dcc-mcp-maya/commit/288b0399d7e64cc3615c92810ddaa3c201d0ac51))
* **server:** wire in-process executor on dispatcher attach ([#142](https://github.com/loonghao/dcc-mcp-maya/issues/142)) ([4fcd6bf](https://github.com/loonghao/dcc-mcp-maya/commit/4fcd6bff289b11d9f252c23342bc430c31503a58))
* **skills:** normalize execute_python/execute_mel params + capture stdout ([#150](https://github.com/loonghao/dcc-mcp-maya/issues/150), [#151](https://github.com/loonghao/dcc-mcp-maya/issues/151), [#153](https://github.com/loonghao/dcc-mcp-maya/issues/153)) ([7aabc19](https://github.com/loonghao/dcc-mcp-maya/commit/7aabc19ed665d3b8b58f7dbd0b9a099bfd27e43d))


### Documentation

* fix tool/skill count errors and add README_zh.md ([35bc326](https://github.com/loonghao/dcc-mcp-maya/commit/35bc326010615eb3e13f1d5091849d8786032c47))
* fix tool/skill count errors and add README_zh.md ([1e82e5a](https://github.com/loonghao/dcc-mcp-maya/commit/1e82e5ac8ef48ae8f6ab657d3cd1b31f33be722d))

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
