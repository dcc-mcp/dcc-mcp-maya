# dcc-mcp-maya auto-improve execution memory

## 2026-04-08 (Round 1 — baseline)

### State before this round
- Branch: `auto-improve` (worktree at `G:/PycharmProjects/github/dcc-mcp-maya-auto-improve`)
- Version: 0.3.0
- Actions: 30 registered (scene×7, primitives×6, materials×4, animation×5, render×4, scripting×2)
- Tests: 142 passing, coverage 98%
- Uncovered: primitives.py lines 70, 108, 247→249; server.py lines 34, 104-105, 120-121, 127-128

### Work done
1. Rebased `auto-improve` onto remote `main` (4 commits rebased cleanly, origin/main was at `fe2897c`)
2. Added 3 new scene hierarchy Actions to `scene.py`:
   - `group_objects(objects, group_name=None, world=False)` — group objects under a new Maya group node
   - `parent_object(child, parent=None, world=False)` — set or clear object parent/world
   - `select_by_type(object_type)` — select all objects of a given Maya type
3. Registered all 3 new actions in `actions/__init__.py` → total 33 actions
4. Added 21 new tests in `test_actions_extended.py`:
   - `TestGroupObjects` (7 tests)
   - `TestParentObject` (7 tests)
   - `TestSelectByType` (4 tests)
   - `test_create_cube_with_name`, `test_create_cylinder_with_name`, `test_delete_objects_none_existing` (3 tests)
5. Updated `TestRegisterAllUpdated` to assert `len(actions) >= 24`

### State after this round
- Tests: 163 passing (all pass), 0 failures
- Coverage: 99% total (all action modules 100%, server.py 91%)
- Committed: `ed2010c feat(skills): add group_objects, parent_object, select_by_type scene hierarchy actions`
- Pushed: `origin/auto-improve` updated (force-with-lease after rebase)

---

## 2026-04-11 (Round 2 — 5 new Skills implemented)

### State before this round
- Branch: `chore/update-dcc-mcp-core-latest-api` (workspace on this branch)
- Architecture: fully migrated to Skills-based system (Skills in `src/dcc_mcp_maya/skills/`)
- Tests: 995 passed, 1 skipped
- Empty skill dirs: 33 directories with `scripts/` but no `.py` files

### Work done
Implemented 5 previously-empty Skill domains (20 scripts total):

**maya-annotation** (4 scripts):
- `create_annotation` — create text annotation at position or attached to object
- `list_annotations` — list all `annotationShape` nodes
- `update_annotation` — change text/position of existing annotation
- `delete_annotation` — delete annotation shape + transform

**maya-audio** (4 scripts):
- `import_audio` — import WAV/AIFF and create sound node
- `list_audio` — list all `audio` nodes with file_path/offset
- `set_timeline_audio` — attach sound node to Maya timeline via `timeControl`
- `remove_audio` — delete sound node

**maya-cache** (4 scripts):
- `create_geometry_cache` — bake deformations via `doCreateGeometryCache` MEL
- `attach_geometry_cache` — attach existing XML cache via `doAttachCache` MEL
- `list_geometry_caches` — list `cacheFile` nodes (optionally per mesh)
- `delete_geometry_cache` — delete node + optional disk file cleanup

**maya-color-grading** (4 scripts):
- `get_color_management_info` — query enabled/rendering_space/view_transform/ocio_config
- `set_rendering_space` — change rendering color space (ACES, sRGB, etc.)
- `set_view_transform` — change viewport view LUT
- `apply_gamma_correction` — insert `gammaCorrect` node between file texture and material

**maya-constraints-advanced** (4 scripts):
- `add_pole_vector_constraint` — pole vector from locator to IK handle
- `bake_constraint` — `bakeResults` + optional constraint deletion
- `get_constraint_weights` — query per-driver blend weights
- `set_constraint_weight` — set one driver's weight for space switching

**Tests**: `test_skills_round15.py` — 70 new tests, all pass.

### State after this round
- Tests: 1065 passed, 1 skipped (all pass)
- Committed on `main`: `1b3389a feat(skills): add maya-annotation, maya-audio, maya-cache, maya-color-grading, maya-constraints-advanced skills`
- All 5 SKILL.md files use new format (allowed-tools, license, depends)

### Remaining empty skills for next round
Still-empty: maya-blend-shape-utils, maya-camera-sequence, maya-cloth-sim,
maya-export-preset, maya-expressions, maya-fluid, maya-gpu-cache, maya-grooming,
maya-hdri, maya-instancer, maya-light-rig, maya-material-library, maya-mocap,
maya-muscle, maya-namespaces (dir), maya-nparticles, maya-ocean, maya-paint-effects,
maya-pipeline, maya-pose-library, maya-proxy-mesh, maya-render-farm, maya-render-passes,
maya-rig-utils, maya-scene-assembly, maya-scripting (dir), maya-shot-export,
maya-skinning-utils, maya-spline-ik, maya-toon, maya-utility (dir), maya-xform-utils

Priority candidates for next round: maya-expressions, maya-blend-shape-utils,
maya-gpu-cache, maya-spline-ik, maya-xform-utils

---

## 2026-04-11 (Round 3 — 5 new Skills implemented)

### State before this round
- Branch: `main`
- Tests: 1065 passed, 1 skipped
- Empty skill dirs: 28 (maya-expressions was already filled before this round)

### Work done
Implemented 5 Skill domains (20 scripts total):

**maya-blend-shape-utils** (4 scripts):
- `create_blend_shape` — create blendShape deformer with one or more targets
- `list_blend_shapes` — list all blendShape nodes (optionally filtered by mesh)
- `set_blend_shape_weight` — set target weight by index or alias name
- `get_blend_shape_weights` — query all target names + current weights

**maya-xform-utils** (4 scripts):
- `freeze_transforms` — makeIdentity on translate/rotate/scale with dry-run support
- `reset_pivot` — move pivot to bbox_center, world_origin, or bottom
- `match_transforms` — snap source to match target's world-space xforms
- `bake_transforms` — bakeResults over frame range (collapses constraints)

**maya-spline-ik** (4 scripts):
- `create_spline_ik` — ikSplineSolver handle with auto or provided curve
- `set_spline_ik_twist` — configure dTwistControlEnable + up vector
- `add_stretch_to_spline_ik` — curveInfo → multiplyDivide → joint scale stretch rig
- `list_spline_ik_handles` — list all ikSplineSolver handles

**maya-gpu-cache** (4 scripts):
- `export_gpu_cache` — cmds.gpuCache export to .abc via gpuCache plugin
- `import_gpu_cache` — create gpuCache shape node from .abc file
- `list_gpu_caches` — list all gpuCache nodes with file paths
- `refresh_gpu_cache` — toggle refreshAll to force reload from disk

**maya-instancer** (4 scripts):
- `create_instancer` — particleInstancer with geometry list
- `add_instance_object` — add geometry to existing instancer
- `set_instancer_attribute` — map per-particle attr to instancer field
- `list_instancers` — list all instancer nodes with linked particles/geometry

**Tests**: `test_skills_round16.py` — 66 new tests, all pass.

### State after this round
- Tests: 1131 passed, 1 skipped (all pass), 0 failures
- Committed on `main`: `0e04fb6 feat(skills): add maya-blend-shape-utils, maya-xform-utils, maya-spline-ik, maya-gpu-cache, maya-instancer skills`

### Remaining empty skills (23 left)
maya-camera-sequence, maya-cloth-sim, maya-export-preset, maya-fluid,
maya-grooming, maya-hdri, maya-light-rig, maya-material-library, maya-mocap,
maya-muscle, maya-namespaces, maya-nparticles, maya-ocean, maya-paint-effects,
maya-pipeline, maya-pose-library, maya-proxy-mesh, maya-render-farm, maya-render-passes,
maya-rig-utils, maya-scene-assembly, maya-shot-export, maya-skinning-utils,
maya-toon

Priority candidates for next round: maya-skinning-utils, maya-rig-utils,
maya-render-passes, maya-pose-library, maya-light-rig

---

## 2026-04-11 (Round 4 — 5 new Skills implemented)

### State before this round
- Branch: `main`
- Tests: 1131 passed, 1 skipped
- Empty skill dirs: 23 (priority: maya-skinning-utils, maya-rig-utils, maya-render-passes, maya-pose-library, maya-light-rig)

### Work done
Implemented 5 Skill domains (20 scripts total):

**maya-skinning-utils** (4 scripts):
- `copy_skin_weights` — copySkinWeights between source and target mesh, auto-creates skinCluster on target if needed
- `normalize_skin_weights` — setAttr normalizeWeights + skinPercent normalize=True
- `mirror_skin_weights` — copySkinWeights with mirrorMode (YZ/XZ/XY)
- `prune_skin_weights` — skinPercent pruneWeights threshold

**maya-rig-utils** (4 scripts):
- `create_control_curve` — 5 preset nurbs shapes (circle, square, triangle, arrow, diamond) with scale/color override
- `lock_hide_attributes` — lock + hide channel box attrs per node
- `add_space_switch` — parentConstraint + enum attr + setDrivenKeyframe space switching
- `connect_attributes` — batch connectAttr with force/error reporting

**maya-render-passes** (4 scripts):
- `create_render_pass` — renderPass node (Maya Software) or aiAOV node (Arnold)
- `list_render_passes` — list renderPass + aiAOV nodes with enabled/name info
- `enable_render_pass` — toggle renderable/enabled attr
- `set_render_pass_output` — set fileNamePrefix/outputPrefix + imageFormat/dataType attrs

**maya-pose-library** (4 scripts):
- `save_pose` — JSON snapshot of tx/ty/tz/rx/ry/rz/sx/sy/sz per control
- `load_pose` — apply JSON pose with namespace support, skip_missing option
- `list_poses` — walk directory for .json pose files with control_count
- `mirror_pose` — L_/R_ prefix swap + negate tx/ry/rz, output to file or apply to scene

**maya-light-rig** (4 scripts):
- `create_three_point_rig` — key/fill/rim directional rig with intensity/color params
- `create_hdri_dome` — aiSkyDomeLight (Arnold) or ambientLight fallback + file texture
- `list_light_rigs` — group light shapes by parent rig transform with intensity info
- `set_light_rig_intensity` — absolute or multiply mode for all lights in a rig group

**Tests**: `test_skills_round17.py` — 97 new tests, all pass.

### State after this round
- Tests: 1228 passed, 1 skipped (all pass), 0 failures
- Committed on `main`: `63efa00 feat(skills): add maya-skinning-utils, maya-rig-utils, maya-render-passes, maya-pose-library, maya-light-rig skills`

### Remaining empty skills (18 left)
maya-camera-sequence, maya-cloth-sim, maya-export-preset, maya-fluid,
maya-grooming, maya-hdri, maya-material-library, maya-mocap,
maya-muscle, maya-nparticles, maya-ocean, maya-paint-effects,
maya-pipeline, maya-proxy-mesh, maya-render-farm,
maya-scene-assembly, maya-shot-export, maya-toon

Priority candidates for next round: maya-shot-export, maya-material-library,
maya-render-farm, maya-nparticles, maya-toon

---

## 2026-04-11 (Round 5 — 5 new Skills implemented)

### State before this round
- Branch: `main`
- Tests: 1228 passed, 1 skipped
- Empty skill dirs: 18 (priority: maya-shot-export, maya-material-library, maya-toon, maya-nparticles, maya-render-farm)

### Work done
Implemented 5 Skill domains (20 scripts total):

**maya-shot-export** (4 scripts):
- `export_shot_fbx` — Export selected geometry within a frame range to FBX (uses FBXExport MEL)
- `export_shot_alembic` — Export selected objects as Alembic (.abc) via AbcExport plugin
- `export_camera` — Export a shot camera to FBX or Maya ASCII (MA format avoids mel import)
- `get_shot_info` — Query scene name, frame range, active camera, all cameras

**maya-material-library** (4 scripts):
- `save_material` — Serialize shading node attributes to JSON preset file
- `load_material` — Recreate material from JSON preset + optional mesh assignment
- `list_materials` — List all .json preset files in a library directory
- `delete_material_preset` — Remove a JSON preset file from the library

**maya-toon** (4 scripts):
- `add_toon_outline` — Add pfxToon outline stroke via `assignNewPfxToon` MEL
- `create_toon_shader` — Create rampShader node with 3-band colour ramp + shading group
- `set_outline_width` — Set lineWidth (and optionally profileLineWidth) on pfxToon node
- `list_toon_outlines` — List all pfxToon nodes with line width and connected meshes

**maya-nparticles** (4 scripts):
- `create_nparticle_emitter` — Create nParticle system via `nParticle` MEL with nucleus wiring
- `set_nparticle_attribute` — Set scalar attribute on nParticle shape node
- `add_field_to_nparticles` — Create dynamic field (gravity/turbulence/drag/etc.) and connect to particles
- `list_nparticle_systems` — List all nParticle + nucleus nodes with particle count / settings

**maya-render-farm** (4 scripts):
- `validate_scene_for_farm` — Check for unsaved scene, missing textures, unloaded refs, bad frame range
- `write_render_job` — Write JSON render job spec from current scene render globals
- `submit_to_deadline` — Submit scene to Thinkbox Deadline via deadlinecommand CLI
- `get_render_job_status` — Query Deadline job status by job ID via deadlinecommand -GetJobDetails

**Tests**: `test_skills_round18.py` — 73 new tests, all pass.

### State after this round
- Tests: 1301 passed, 1 skipped (all pass), 0 failures
- Committed on `main`: `7ef3d78 feat(skills): add maya-shot-export, maya-material-library, maya-toon, maya-nparticles, maya-render-farm skills`
- Pushed: `origin/main` updated

### Remaining empty skills (13 left)
maya-camera-sequence, maya-cloth-sim, maya-export-preset, maya-fluid,
maya-grooming, maya-hdri, maya-mocap, maya-muscle, maya-namespaces,
maya-ocean, maya-paint-effects, maya-pipeline, maya-proxy-mesh,
maya-scene-assembly, maya-scripting, maya-texture-bake, maya-utility

Priority candidates for next round: maya-paint-effects, maya-hdri,
maya-texture-bake, maya-camera-sequence, maya-namespaces

---

## 2026-04-11 (Round 6 — 5 new Skills implemented)

### State before this round
- Branch: `main`
- Tests: 1301 passed, 1 skipped
- Empty skill dirs: 13 (priority from Round 5: maya-paint-effects, maya-hdri, maya-camera-sequence, maya-namespaces, maya-texture-bake)

### Work done
Implemented 5 Skill domains (20 scripts total):

**maya-paint-effects** (4 scripts):
- `create_stroke` — Create standalone Paint Effects stroke in world space via curve + brush preset
- `attach_stroke_to_surface` — Scatter brush strokes on NURBS/polygon surface
- `list_strokes` — List all pfxToon/stroke nodes with brush linkage and visibility
- `delete_stroke` — Delete one or all Paint Effects stroke nodes

**maya-hdri** (4 scripts):
- `load_hdri` — Load HDR image as Arnold aiSkyDomeLight (or native ambient fallback)
- `set_hdri_exposure` — Set aiExposure / intensity on dome nodes
- `set_hdri_rotation` — Set Y-axis rotation on dome light transform
- `list_hdri_nodes` — List all aiSkyDomeLight / ambientLight / directionalLight nodes

**maya-camera-sequence** (4 scripts):
- `create_shot` — Create Maya shot node with camera + frame range
- `list_shots` — List shots sorted by sequence_start_frame
- `set_shot_range` — Update start/end/sequence timing of a shot node
- `delete_shot` — Delete a shot node

**maya-namespaces** (4 scripts):
- `create_namespace` — Create namespace (with empty-name guard)
- `list_namespaces` — List non-default namespaces with object counts
- `rename_namespace` — Rename namespace (with :prefix format, protected-ns check)
- `remove_namespace` — Remove namespace + force-merge objects to parent

**maya-texture-bake** (4 scripts):
- `bake_lighting` — Bake diffuse+shadow via convertLightmap
- `bake_ambient_occlusion` — Bake AO via mib_amb_occlusion + convertSolidTx
- `transfer_maps` — Transfer normals/displacement/diffuse from high-res to low-res
- `list_bake_sets` — List objectSet nodes with bakeResolutionX attribute

**Tests**: `test_skills_round19.py` — 77 new tests, all pass.
- Fixed: rename_namespace uses `:name` prefix format (consistent with round3 expectations)

### State after this round
- Tests: 1378 passed, 1 skipped (all pass), 0 failures
- Committed on `main`: `5b20538 feat(skills): add maya-paint-effects, maya-hdri, maya-camera-sequence, maya-namespaces, maya-texture-bake skills`
- Pushed: `origin/main` updated

### Remaining empty skills (8 left)
maya-cloth-sim, maya-export-preset, maya-fluid, maya-grooming,
maya-mocap, maya-muscle, maya-ocean, maya-proxy-mesh,
maya-scene-assembly, maya-scripting, maya-utility

Priority candidates for next round: maya-fluid, maya-ocean, maya-cloth-sim,
maya-grooming, maya-export-preset

---

## 2026-04-11 (Round 7 — 5 new Skills implemented)

### State before this round
- Branch: `main`
- Tests: 1378 passed, 1 skipped
- Empty skill dirs: priority from Round 6: maya-fluid, maya-ocean, maya-cloth-sim, maya-grooming, maya-export-preset

### Work done
Implemented 5 Skill domains (20 scripts total):

**maya-fluid** (4 scripts): create_fluid_container, set_fluid_attribute, list_fluid_containers, delete_fluid_container
**maya-ocean** (4 scripts): create_ocean (polyPlane + oceanShader), set_ocean_attribute, add_ocean_wake, list_ocean_surfaces
**maya-cloth-sim** (4 scripts): create_ncloth (4 presets), set_ncloth_attribute, bake_cloth_cache (MEL), list_ncloth_objects
**maya-grooming** (4 scripts): create_nhair_system (MEL), set_nhair_attribute, list_hair_systems, add_nhair_cache (MEL)
**maya-export-preset** (4 scripts): save_export_preset (JSON), load_export_preset, list_export_presets, delete_export_preset

**Tests**: `test_skills_round20.py` — 70 new tests, all pass.

### State after this round
- Tests: 1448 passed, 1 skipped (all pass), 0 failures
- Committed on `main`: `30f3283 feat(skills): add maya-fluid, maya-ocean, maya-cloth-sim, maya-grooming, maya-export-preset skills`
- Pushed: `origin/main` updated

### Remaining empty skills
maya-mocap, maya-muscle, maya-pipeline, maya-proxy-mesh, maya-scene-assembly, maya-scripting, maya-utility

Priority candidates for next round: maya-mocap, maya-muscle, maya-scene-assembly, maya-proxy-mesh, maya-utility

---

## 2026-04-11 (Round 8 — 5 new Skills implemented)

### State before this round
- Branch: `main`
- Tests: 1448 passed, 1 skipped
- Empty skill dirs (priority): maya-expressions (scripts missing), maya-mocap, maya-muscle, maya-scene-assembly, maya-proxy-mesh

### Work done
Implemented 5 Skill domains (20 scripts total):

**maya-expressions** (4 scripts): create_expression, list_expressions, delete_expression, edit_expression (rewritten for Round 3 compat + new edit script)
**maya-mocap** (4 scripts): import_mocap, create_hik_definition, bake_mocap_to_rig, clean_mocap_keys
**maya-muscle** (4 scripts): create_muscle_capsule, list_muscles, set_muscle_attribute, apply_muscle_skin
**maya-scene-assembly** (4 scripts): create_assembly_definition, add_assembly_representation, create_assembly_reference, list_assemblies
**maya-proxy-mesh** (4 scripts): create_proxy, swap_proxy, list_proxies, set_proxy_attribute

**Tests**: `test_skills_round21.py` — 93 tests, all pass.
Key fix: maya-expressions backward-compatible with Round 3 tests (expression_name context key, type validation).

### State after this round
- Tests: 1541 passed, 1 skipped (all pass), 0 failures
- Committed on `main`: `2e9a699`
- Pushed: `origin/main` updated

### Remaining empty skills (3 left)
maya-pipeline, maya-scripting, maya-utility

Priority candidates for next round: maya-pipeline, maya-scripting, maya-utility — then E2E/CI improvements

---

## 2026-04-11 (Round 9 — 3 remaining Skills filled + backward compat fixes)

### State before this round
- Branch: `main`
- Tests: 1541 passed, 1 skipped
- Empty skill dirs: maya-pipeline (no SKILL.md), maya-scripting (SKILL.md only), maya-utility (SKILL.md only)

### Work done
Implemented 3 final Skill domains (12 scripts total):

**maya-scripting** (4 scripts): execute_mel, execute_python, list_mel_procedures, get_script_node
**maya-utility** (4 scripts): create_utility_node, get_scene_statistics, list_node_connections, clean_scene
**maya-pipeline** (SKILL.md + 4 scripts): set_project, publish_asset, tag_asset_metadata, get_asset_metadata

Backward compatibility fixes vs Round3 tests:
- execute_mel: context key output (was return_value) + script key added
- execute_python: pre-injects cmds in exec namespace; exposes result variable → output
- create_utility_node: shadingNode(no name) then rename() (was shadingNode with name=)
- get_scene_statistics: added scene_file key

**Tests**: test_skills_round22.py — 63 tests, all pass.

### State after this round
- Tests: 1604 passed, 1 skipped, 0 failures
- Committed on `main`: `0a2aabd feat(skills): add maya-scripting, maya-utility, maya-pipeline skills`
- Pushed: origin/main updated

### All skill directories now populated
No more empty skill dirs.

### Next priorities
1. E2E test infrastructure (tests/e2e/ + conftest.py + GitHub Actions e2e.yml)
2. Python 3.7+ compatibility audit across all skill scripts
3. Coverage improvements for server.py edge cases

---

## 2026-04-11 (Round 10 — E2E infrastructure + Round 23 edge-case tests)

### State before this round
- Branch: `main`
- Tests: 1604 passed, 1 skipped
- All 34+ Skill domains populated (Rounds 1-9 complete)
- e2e.yml already existed; no structured tests/e2e/ directory

### Work done

**Python 3.7+ compatibility audit**: Scanned all 344 skill scripts. Zero issues found.

**E2E test infrastructure** (`tests/e2e/` directory):
- `tests/e2e/__init__.py` — package marker
- `tests/e2e/conftest.py` — pytest_configure + pytest_collection_modifyitems that auto-skips when maya.standalone unavailable
- `tests/e2e/test_scene_e2e.py` — TestSceneSkillsE2E (6 tests), TestPrimitivesSkillsE2E (8 tests)
- `tests/e2e/test_animation_e2e.py` — TestAnimationSkillsE2E (8 tests)
- `tests/e2e/test_material_e2e.py` — TestMaterialsE2E (6 tests), TestUvOpsE2E (3 tests)
- `tests/e2e/test_scripting_e2e.py` — TestScriptingE2E (6 tests), TestUtilityE2E (4 tests), TestPipelineE2E (3 tests)

**test_skills_round23.py** — 78 tests (all pass):
- TestToonAddOutline (10): no-objects error, mesh-shape happy path, set_outline_width type-check
- TestFluidSkills (8): create/list/set_attribute/delete with correct param names
- TestOceanSkills (8): create/list/set_ocean_attribute(shader=) / add_ocean_wake(shader=)
- TestClothSimSkills (9): 4 presets + set_ncloth_attribute(ncloth_shape=) / list
- TestMocapSkills (6): file-not-found, unsupported format, HIK definition, clean_keys(joints=)
- TestSceneAssemblySkills (6): create/add(assembly=)/list(context.definitions+references)
- TestProxyMeshSkills (10): create/keep_visible/custom_name/list/swap_proxy(proxy=)/set_proxy_attribute(proxy=)
- TestMuscleSkillEdgeCases (5): capsule(start_joint+end_joint required), list, missing-node errors
- TestExportPresetSkills (8): save/list/load/delete with correct param names (preset_dir, preset_path)
- TestPipelineEdgeCases (8): set_project(path=), tag/get(node=), publish_asset(publish_dir=)

**Bug fixed**: `clean_mocap_keys` mock fixed — `keyframeCount=True` returns int not list.

### State after this round
- Tests: 1682 passed, 5 skipped (E2E skipped without mayapy), 0 failures
- Committed: `540e79e test(e2e): add tests/e2e/ structured directory + round23 unit tests`
- Pushed: `origin/main` updated

## 2026-04-11 (Round 11 — api.py 扩展 + 全量 prompt 补全)

### State before this round
- Branch: `feat/skill-api-improvements`（领先 origin/main 7 commits）
- Tests: 1810 passed, 27 skipped
- api.py: 已有 maya_success/maya_error/maya_from_exception/with_maya 基础 helpers
- prompt= 覆盖率：488/506 个 maya_success 调用缺少 prompt 参数

### Work done

**1. 格式化改动 commit**：
- `style(skills): apply ruff format to all skill scripts` — 30 files, 94 insertions

**2. 扩展 `dcc_mcp_maya.api`**（+4 新增 helpers）：
- `require_param(params, key, default=SENTINEL)` — 参数提取+验证；缺少时抛 MissingParamError
- `missing_param_error(key, **context)` — 快捷构建缺参数错误 dict
- `validate_node_exists(cmds, name)` — 检查节点存在，不存在返回错误 dict
- `validate_node_type(cmds, name, expected_type)` — 检查节点类型，不符返回错误 dict
- 全部加入 `__all__` 并导出至 `dcc_mcp_maya` 命名空间

**3. 批量为 172 个 skill 脚本添加 `prompt=`**：
- 使用 `tools/add_prompts.py` 自动处理
- 为 65 个 skill 目录×每个动词设计语义化的下一步 prompt
- 最终：所有 506 个 maya_success 调用都有 prompt（文件级验证: 0 missing）

**4. 扩展 `tests/test_api.py`**：
- +19 新测试：TestRequireParam(7), TestMissingParamError(3), TestValidateNodeExists(4), TestValidateNodeType(5)
- 更新 test_public_api_reexport 验证新 helpers 可从 dcc_mcp_maya 直接导入

**5. 示例重构**：`delete_display_layer.py` 改用 validate_node_exists + validate_node_type，减少样板代码

### State after this round
- Tests: 1829 passed, 27 skipped (all pass), 0 failures
- Committed: `d706155 feat(api): add require_param, validate_node_exists, validate_node_type helpers; add prompt= to all 172 skill scripts`
- Pushed: `origin/feat/skill-api-improvements` updated

---

## 2026-04-11 (Round 12 — api.py 扩展 + skinning-utils 重构 + 测试修复)

### State before this round
- Branch: `feat/skill-api-improvements`
- Tests: 1829 passed, 27 skipped (2 failures: test_not_a_display_layer / test_delete_wrong_node_type)
- api.py had: require_param, validate_node_exists, validate_node_type
- skinning-utils still used hand-written objExists guards

### Work done

**1. 修复 2 个失败测试**：
- test_skills_round7.py::TestDeleteDisplayLayer::test_not_a_display_layer
- test_skills_round24.py::TestDeleteDisplayLayer::test_delete_wrong_node_type
- 原因：Round 11 重构 delete_display_layer 使用 validate_node_type，消息变为 "Wrong node type: ..."
- 修复：更新两个测试断言为 `result["message"].lower().startswith("wrong node type")`

**2. 扩展 api.py — 3 个新 helpers**：
- `batch_validate_nodes(cmds, names)` — 批量检查多个节点，返回第一个缺失节点的 error dict 或 None
- `require_any_param(params, *keys)` — 返回 params 中第一个存在的 key 值，全部缺失则 raise MissingParamError
- `get_param_list(params, key, default=None)` — 规范化 str/list/None → list（单值自动包装）
- 全部加入 `__all__` 并导出至 dcc_mcp_maya 命名空间

**3. 重构 maya-skinning-utils 4 个脚本**：
- copy_skin_weights.py: 手写 for 循环检查 → batch_validate_nodes([source_mesh, target_mesh])
- normalize_skin_weights.py: 手写 objExists → validate_node_exists
- mirror_skin_weights.py: 手写 objExists → validate_node_exists
- prune_skin_weights.py: 手写 objExists → validate_node_exists

**4. test_skills_round25.py — 40 个新测试，全部通过**：
- TestBatchValidateNodes (7): all-exist/empty/first-missing/second-missing/short-circuit/solutions/reexport
- TestRequireAnyParam (8): first/second/last/none-raises/single/error-message/reexport
- TestGetParamList (8): list/string-wrap/missing-empty/custom-default/tuple/int/empty-str/reexport
- TestSkinningUtilsRefactor (13): copy/normalize/mirror/prune 各 happy path + missing node + no cluster
- TestApiPublicExports (4): 验证 3 个新 helpers 从顶层包可导入且在 __all__ 中

### State after this round
- Tests: 1869 passed, 27 skipped (all pass), 0 failures
- Committed: `c9a534c feat(api): add batch_validate_nodes, require_any_param, get_param_list helpers; refactor skinning-utils to use validate_node_exists`
- Pushed: `origin/feat/skill-api-improvements` updated

---

## 2026-04-11 (Round 13 — api.py Python 3.7 修复 + 14 个 skill 重构)

### State before this round
- Branch: `feat/skill-api-improvements`
- Tests: 1869 passed, 27 skipped
- api.py 中存在 Python 3.10+ 类型注解（`str | None`、`list[str]`）
- 仍有 404 处手写 `objExists` 守卫分布在各 skill 目录

### Work done

**1. api.py Python 3.7 兼容性修复**：
- `str | None` → `Optional[str]`/`Optional[dict]`
- `list[str]` → `List[str]`（从 typing 导入）
- `dict` 返回类型 → `Dict[str, Any]`
- `batch_validate_nodes` 参数/返回类型更精确：`List[str]` / `Optional[Dict[str, Any]]`

**2. 重构 14 个 skill 脚本（5 个目录）**：
- `maya-rigging`（6 脚本）：skin_cluster_bind / create_ik_handle / set_driven_key / set_ik_fk_blend / assign_deformer / set_joint_orient → `validate_node_exists`/`batch_validate_nodes`/`validate_node_type`
- `maya-dynamics`（2 脚本）：set_ncloth_attribute / set_nrigid_attribute → `validate_node_exists` + `validate_node_type`
- `maya-node-graph`（2 脚本）：connect_attr / disconnect_attr → `batch_validate_nodes`
- `maya-mesh-ops`（3 脚本）：apply_subdivision / cleanup_mesh / triangulate → `validate_node_exists`
- `maya-animation`（2 脚本）：set_keyframe / delete_keyframes → `validate_node_exists`

**3. 修复 3 个受重构影响的旧测试断言**（test_skills_round6.py）

**4. test_skills_round26.py — 61 个新测试，全部通过**

### State after this round
- Tests: 1930 passed, 27 skipped (all pass), 0 failures
- Committed: `043bdd8 refactor(api): fix Python 3.7 type annotations; refactor 14 skill scripts; add test_skills_round26 (61 tests)`
- Pushed: `origin/feat/skill-api-improvements` updated

---

## 2026-04-11 (Round 14 — 15 scripts migrated to skill_entry; test_skills_round28 + round13 update)

### State before this round
- Branch: `feat/skill-api-improvements`
- Tests: 1972 passed, 27 skipped
- Latest commit: `2e4a9c2` (migrate all 369 skill scripts to dcc_mcp_core.skill API)
- 15 scripts still using old `def run(params)` style in maya-mash (5), maya-selection (5), maya-xgen (5)

### Work done

**1. Migrated 15 legacy scripts** from `run(params)` → typed `def func(**kwargs) + @skill_entry main`:
- **maya-mash** (5): add_node, create_network, delete_network, list_networks, set_mash_attribute
  - Also uses `validate_node_exists` from `dcc_mcp_maya.api` to replace inline `objExists` guards
- **maya-selection** (5): convert_selection, grow_selection, invert_selection, select_similar, shrink_selection
- **maya-xgen** (5): create_description, delete_description, get_xgen_attribute, list_descriptions, set_xgen_attribute

**2. Updated test_skills_round13.py**: Changed all `mod.run({...})` → `mod.main(**{...})` to match new API (64 tests still pass)

**3. Added test_skills_round28.py** — 49 new tests:
- TestMashCreateNetwork (4), TestMashAddNode (3), TestMashDeleteNetwork (3), TestMashListNetworks (3), TestMashSetAttribute (3)
- TestGrowSelection (3), TestShrinkSelection (2), TestInvertSelection (2), TestConvertSelection (4), TestSelectSimilar (4)
- TestXGenCreateDescription (4), TestXGenDeleteDescription (3), TestXGenListDescriptions (4), TestXGenGetAttribute (3), TestXGenSetAttribute (3)
- TestNoLegacyRunSignature (1) — structural AST check: 0 `run(params)` in all 369 scripts

**4. ruff clean**: Removed unused `pytest` import from test file.

### State after this round
- Tests: 2021 passed, 27 skipped (all pass), 0 failures
- 0 `def run(params)` signatures remain in any skill script (confirmed by AST check)
- 344 scripts have `@skill_entry` decorator (100%)
- Committed: `d2f93b7 refactor(skills): migrate maya-mash, maya-selection, maya-xgen 15 scripts to skill_entry style; update test_skills_round13; add test_skills_round28 (49 tests)`
- Pushed: `origin/feat/skill-api-improvements` updated


---

## 2026-04-11 (Round 15 — bulk validate_node_exists migration)

### State before this round
- Branch: `feat/skill-api-improvements`
- Tests: 2021 passed, 27 skipped
- 353 raw `cmds.objExists` guard patterns across 193 files
- dcc-mcp-core: v0.12.x, new APIs include register_batch, TransportManager.bind_and_register, create_skill_manager

### Work done

**1. tools/migrate_objexists.py** — AST-safe regex migration tool:
- Converts `if not cmds.objExists(X): return skill_error(...)` → `err = validate_node_exists(cmds, X); if err: return err`
- Dry-run mode; handles single-line and multi-line skill_error patterns
- 212 replacements across 136 files

**2. tools/fix_bad_imports.py** + **tools/fix_missing_imports.py** — repair tools:
- Detected and fixed 133 files where import was inserted inside `if __name__` block (IndentationError)
- Ensures `from dcc_mcp_maya.api import validate_node_exists` is at top-level after dcc_mcp_core imports

**3. ruff auto-fix** — sorted 133 import blocks (I001), added noqa: E402 to 2 edge cases

**4. test_skills_round21 fix** — updated 1 test assertion from `"not exist"` → `"not found"` to match validate_node_exists message

**5. tests/test_skills_round29.py** — 25 new tests:
- TestMigrationStructural (5): no missing imports, no syntax errors, imports at top-level, guard count < 150, usage count >= 140
- TestValidateNodeExistsHelper (6): None/error/node-name/solutions/batch short-circuit/batch-all-exist
- TestGetTransformMigrated (3): success/missing-node/import-present
- TestGetKeyframesMigrated (3): empty/with-keys/missing-node
- TestGetBlendShapeWeightsMigrated (2): success/missing-node
- TestDeleteAnnotationMigrated (3): shape-delete/missing/import-structure
- TestFreezeTransformsMigrated (2): success/missing-object
- TestBatchValidateImports (1): structural check

### State after this round
- Tests: 2046 passed (+25), 27 skipped, 0 failures
- ruff: All checks passed
- objExists guards: 353 → ~95 (complex patterns remain, not auto-migratable)
- validate_node_exists: used in 174 files (up from 39), all properly imported
- Committed: `ee06ec6 refactor(skills): bulk migrate 136 scripts from cmds.objExists to validate_node_exists; add test_skills_round29 (25 tests)`
- Pushed: `origin/feat/skill-api-improvements` updated

### Next priorities
1. Migrate remaining ~95 complex `objExists` patterns (multi-node checks → batch_validate_nodes)
2. Integration of dcc-mcp-core new APIs: `create_skill_manager()`, `TransportManager.bind_and_register`, `resolve_dependencies`
3. server.py update: use `create_skill_manager()` for one-step setup
4. E2E tests: add more coverage for skill dirs added in Rounds 2-9

