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

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Missing actions to consider:
  - `lock_object` / `unlock_object` — lock/unlock transform attributes
  - `duplicate_object` — duplicate with optional instance
  - `freeze_transforms` — apply transforms to shape
  - `center_pivot` — center object pivot point
  - `get_bounding_box` — query world-space bounding box
  - `set_visibility` — show/hide objects
  - `get_scene_info` (detailed) — full DAG hierarchy query

---

## 2026-04-10 (Round 2 — skills Skill test coverage expansion)

### Context
- Working on `feat/skills-sop` branch (not `auto-improve`, but the skill work is forward-compatible)
- Baseline: 96 tests passing (1 skipped)

### Work done
1. **Bug fixes** (3 source files):
   - `maya-deformers/create_cluster.py`: `Dict` missing from `typing` import → added and then ruff auto-removed unused
   - `maya-deformers/create_lattice.py`: same `Dict` import issue → fixed
   - `maya-texture-bake/bake_textures.py`: `error_result()` called with only 1 arg (missing `error` 2nd arg) → fixed
2. **New test file** `tests/test_skills_round3.py` — 92 tests for 6 previously untested Skill groups:
   - `maya-expressions`: `create_expression` (7), `list_expressions` (4), `delete_expression` (4)
   - `maya-namespaces`: `set_namespace` (5), `rename_namespace` (5), `delete_namespace` (5)
   - `maya-scripting`: `execute_mel` (4), `execute_python` (5)
   - `maya-utility`: `create_utility_node` (4), `get_scene_statistics` (3)
   - `maya-vertex-color`: `create_color_set` (5), `set_vertex_color` (5), `get_vertex_color` (4)
   - `maya-deformers`: `create_cluster` (6), `create_lattice` (7), `wire_deformer` (6)
   - `maya-texture-bake`: `bake_textures` (7), `set_color_management` (4), `list_color_spaces` (2)

### State after this round
- Tests: **188 passed, 1 skipped** (was 96)
- All ruff E/W/F checks pass (0 errors)
- Committed: `fde9b63 test(skills): add round3 tests for expressions/namespaces/scripting/utility/vertex-color/deformers/texture-bake; fix bake_textures error_result missing arg`
- Branch: `feat/skills-sop` (not pushed yet)

### Remaining gaps for Round 3
- Skills still missing tests:
  - `maya-rigging/scripts/` — skinCluster, joint chain, IK handle etc.
  - `maya-mesh-ops/scripts/` — boolean, smooth, triangulate etc.
  - `maya-node-graph/scripts/` — connect_attributes, disconnect etc.
  - `maya-sets/scripts/` — create_set, add_to_set etc.
  - `maya-references/scripts/` — create_reference, list_references etc.
  - `maya-render-layers/scripts/` — create_render_layer etc.
  - `maya-scene-utils/scripts/` — optimize_scene etc.
  - `maya-uv-ops/scripts/` — auto_uv, layout_uv etc.
- All Skill `scripts/` are now populated; no more empty dirs
- `tests/e2e/` directory does not yet exist; E2E tests with `tahv/docker-mayapy` not yet added
- `.github/workflows/e2e.yml` not yet created

---

## 2026-04-10 (Round 3 — rigging/mesh-ops/sets/node-graph test coverage)

### Context
- Branch: `feat/skills-sop`
- Baseline: 188 tests passing (1 skipped)

### Work done
1. Created `tests/test_skills_round4.py` — 75 new tests across 4 Skill groups:
   - `maya-rigging`: `create_joint` (6), `create_ik_handle` (6), `skin_cluster_bind` (5), `mirror_joints` (5), `create_blend_shape` (4), `blend_shape_add_target` (4)
   - `maya-mesh-ops`: `triangulate` (3), `combine_meshes` (5), `mirror_mesh` (5), `get_poly_count` (4)
   - `maya-sets`: `create_set` (5), `add_to_set` (5), `list_sets` (4)
   - `maya-node-graph`: `connect_attr` (5), `disconnect_attr` (4), `list_connections` (5)
2. Fixed 2 test bugs during development:
   - `blend_shape_add_target` test: `cmds.blendShape(geometry=True)` mock must return list, not int
   - `add_to_set` test: error message is `'Not an object set: ...'` (lowercase match)
3. All ruff checks pass (0 errors)

### State after this round
- Tests: **263 passed, 1 skipped** (was 188)
- Committed: `6ab1c08 test(skills): add round4 tests for rigging/mesh-ops/sets/node-graph; 75 new tests, all pass`
- Branch: `feat/skills-sop`

### Remaining gaps for Round 4
- Skills still missing tests (from the original list):
  - `maya-references/scripts/` — create_reference, list_references, import_reference, remove_reference
  - `maya-render-layers/scripts/` — create_render_layer, set_renderable, assign_to_render_layer
  - `maya-scene-utils/scripts/` — optimize_scene, unlock_normals, freeze_transforms
  - `maya-uv-ops/scripts/` — auto_uv, layout_uv, set_uv_tile
  - `maya-rigging/scripts/` still has uncovered: `assign_deformer`, `create_curve`, `set_driven_key`, `set_ik_fk_blend`, `set_joint_limit`, `set_joint_orient`
  - `maya-mesh-ops/scripts/` still has uncovered: `apply_subdivision`, `cleanup_mesh`, `create_proxy_mesh`, `extract_faces`, `get_mesh_edge_info`, `merge_vertices`, `select_by_material`, `separate_mesh`
  - `maya-node-graph/scripts/` uncovered: `apply_symmetry`, `delete_history`, `get_dag_path`, `list_history`, `smooth_mesh`, `transfer_attributes`
- `tests/e2e/` directory does not yet exist
- `.github/workflows/e2e.yml` not yet created

---

## 2026-04-10 (Round 4 — references/render-layers/scene-utils/uv-ops/rigging/mesh-ops/node-graph test coverage)

### Context
- Branch: `feat/skills-sop`
- Baseline: 263 tests passing (1 skipped)

### Work done
1. Created `tests/test_skills_round5.py` — 167 new tests across 7 Skill groups:
   - `maya-references`: `create_reference` (6), `list_references` (4), `remove_reference` (4), `reload_reference` (4), `unload_reference` (2), `list_namespaces` (3)
   - `maya-render-layers`: `create_render_layer` (5), `list_render_layers` (3), `set_render_layer` (4), `delete_render_layer` (5), `set_render_layer_attribute` (4)
   - `maya-scene-utils`: `align_objects` (9), `set_object_color` (5), `set_pivot` (5), `set_shading_mode` (7)
   - `maya-uv-ops`: `project_uvs` (6), `unfold_uvs` (5), `normalize_uvs` (4), `get_uv_info` (4), `create_uv_set` (5)
   - `maya-rigging` (remaining): `assign_deformer` (6), `create_curve` (5), `set_driven_key` (5)
   - `maya-mesh-ops` (remaining): `apply_subdivision` (6), `cleanup_mesh` (3), `create_proxy_mesh` (5), `extract_faces` (5), `merge_vertices` (3), `select_by_material` (4), `separate_mesh` (4), `get_mesh_edge_info` (4)
   - `maya-node-graph` (remaining): `apply_symmetry` (4), `delete_history` (2), `get_dag_path` (3), `list_history` (4), `smooth_mesh` (5), `transfer_attributes` (5)
2. Fixed module-loading pattern: used `importlib.util` (same as round4) to handle hyphenated directory names; no `dcc_mcp_core` in mock modules (real library used)

### State after this round
- Tests: **430 passed, 1 skipped** (was 263)
- All ruff E/W/F checks pass (0 errors)
- Committed: `9b4ee5b test(skills): add round5 tests for references/render-layers/scene-utils/uv-ops/rigging/mesh-ops/node-graph; 167 new tests, all pass`
- Branch: `feat/skills-sop`

### Remaining gaps for Round 5
- Skills still needing tests:
  - `maya-rigging/scripts/` uncovered: `set_ik_fk_blend`, `set_joint_limit`, `set_joint_orient`
  - `maya-attributes/scripts/` — `add_attribute`, `delete_attribute`, `get_attribute`, `list_attributes`, `set_attribute`
  - `maya-cameras/scripts/` — all camera scripts
  - `maya-dynamics/scripts/` — all dynamics scripts
  - `maya-lighting/scripts/` — if any scripts exist
  - `maya-constraints/scripts/` — if any scripts exist
  - `maya-display/scripts/` — if any scripts exist
- `tests/e2e/` directory does not yet exist
- `.github/workflows/e2e.yml` not yet created

---

## 2026-04-10 (Round 6 — maya-scene ext / maya-materials ext / maya-rigging remaining / maya-animation ext)

### Context
- Branch: `feat/skills-sop`
- Baseline: 597 tests passing (1 skipped)

### Work done
1. **`tests/test_skills_round8.py`** — 95 new tests:
   - `maya-scene` (extended scripts): `duplicate_object` (6), `freeze_transforms` (4), `center_pivot` (4), `get_bounding_box` (4), `set_visibility` (5), `lock_object` (5), `get_scene_info` (4), `export_scene` (4), `set_frame_rate` (5), `list_cameras` (5), `create_locator` (5)
   - `maya-materials` (extended): `set_material_attribute` (6), `get_material_connections` (5), `get_shader_assignment` (4), `list_shading_groups` (4), `reset_to_default_material` (4)
   - `maya-rigging` (remaining): `set_ik_fk_blend` (8), `set_joint_limit` (7), `set_joint_orient` (6)
2. **`tests/test_skills_round9.py`** — 49 new tests:
   - `maya-animation` (extended): `set_current_time` (5), `query_scene_time_info` (3), `delete_keyframes` (5), `list_animation_curves` (5), `set_animation_curve_tangent` (8), `bake_simulation` (6), `bake_constraints` (7), `export_animation_curves` (5), `import_animation_curves` (5)
3. All ruff E/W/F checks pass (0 errors)

### State after this round
- Tests: **741 passed, 1 skipped** (was 597)
- Committed: `7ace054 test(skills): add round8/round9 tests; cover maya-scene ext/maya-materials ext/maya-rigging remaining/maya-animation ext; 741 tests total`
- Branch: `feat/skills-sop`
- E2E: `tests/test_e2e_maya_standalone.py` + `.github/workflows/e2e.yml` already exist from prior work

### Remaining gaps for Round 7
- `maya-render/scripts/` — capture_viewport, playblast, render_frame, set_render_settings (no unit tests)
- `maya-scene/scripts/` — open_scene, group_objects, parent_object, select_by_type (verify coverage)
- Python 3.7 compatibility audit across new scripts (`:=` walrus, `X | Y` unions, built-in generics)
- `dcc-mcp-core` API: SkillWatcher hot-reload integration test
- ActionPipeline middleware unit test (server.py coverage lines 172-177, 233-235)

---

## 2026-04-10 (Round 7 — maya-render + maya-primitives test coverage)

### Context
- Branch: `feat/skills-sop`
- Baseline: 741 tests passing (1 skipped)

### Work done
1. **`tests/test_skills_round10.py`** — 42 new tests for `maya-render` Skill (8 scripts):
   - `set_render_settings` (8): width/height, renderer, frame range, format codes (png/exr/unknown), output path, no-settings error, exception
   - `get_render_settings` (4): basic success, format name resolution, unknown code, exception
   - `get_scene_render_stats` (4): basic success, quality attrs queried, attrs skipped when missing, exception
   - `set_render_quality` (7): low/medium/high presets, invalid preset, attrs skipped, exception, case-insensitive
   - `capture_viewport` (4): base64 image success, current-time default, exception, custom dimensions
   - `playblast` (5): success, prompt present, file-not-found, exception, custom percent
   - `import_file` (5): basic import, namespace kwarg, merge_namespaces, empty, exception
   - `export_selection` (5): basic, custom file type, result path, exception, maya ASCII
   - **Bug discovered and fixed**: mock `sys.modules['maya']` must have `.cmds = mock_cmds` (not a bare MagicMock) for `import maya.cmds as cmds` to resolve correctly inside dynamically loaded scripts

2. **`tests/test_skills_round11.py`** — 39 new tests for `maya-primitives` Skill (8 scripts):
   - `create_sphere` (5), `create_cube` (5), `create_cylinder` (4), `create_plane` (4)
   - `delete_objects` (5), `get_transform` (4), `set_transform` (7), `rename_object` (5)
   - Applied the `mock_maya.cmds = mock_cmds` fix throughout

### State after this round
- Tests: **822 passed, 1 skipped** (was 741)
- All ruff checks pass (0 errors)
- Commits: `b39f6bd` (round10), `957e96e` (round11) on `feat/skills-sop`

### Remaining gaps for Round 8
- Python 3.7 compatibility audit: some scripts use f-strings with `{obj}` — these are fine (Python 3.6+). Need to check for walrus `:=`, `X | Y` union types, built-in generics `list[str]` etc.
- `server.py` lines 172-177, 233-235 — ActionPipeline middleware test
- `tests/e2e/` and `.github/workflows/e2e.yml` — still not created
- All skill directories now covered with unit tests (maya-render ✓, maya-primitives ✓)

---

## 2026-04-10 (Round 8 — scene-utils/uv-ops/vertex-color/deformers remaining scripts + bug fixes)

### Context
- Branch: `feat/skills-sop`
- Baseline: 822 tests passing (1 skipped)

### Work done
1. **Bug fixes** (5 source files):
   - `tests/test_skills_round8.py`: 删除未使用变量 `cmds_ov`（ruff F841）
   - `maya-uv-ops/copy_uvs.py`: `error_result()` 单参数 → 补充第二参数；删除 `# type: Dict` 注释
   - `maya-uv-ops/delete_uv_set.py`: 3处 `error_result()` 单参数 → 修复
   - `maya-uv-ops/get_uv_shell_info.py`: 2处 `error_result()` 单参数 → 修复
   - `maya-vertex-color/remove_vertex_colors.py`: 2处 `error_result()` 单参数 → 修复
   - `maya-deformers/sculpt_deformer.py`: 删除 `# type: Dict` 注释
2. **`tests/test_skills_round12.py`** — 53 new tests:
   - `maya-scene-utils`: `create_annotation` (7), `create_polygon_text` (6), `toggle_gpu_override` (5)
   - `maya-uv-ops`: `copy_uvs` (5), `delete_uv_set` (5), `get_uv_shell_info` (5)
   - `maya-vertex-color`: `remove_vertex_colors` (5)
   - `maya-deformers`: `sculpt_deformer` (7), `set_cluster_weights` (8)
3. ruff: 0 errors after all fixes

### State after this round
- Tests: **875 passed, 1 skipped** (was 822)
- Committed: `fe27325` on `feat/skills-sop`

### Remaining gaps for Round 9
- `server.py` ActionPipeline/McpHttpServer 覆盖 (lines ~172-182) — 需更深 mock
- 所有 Skill 目录均已有单元测试覆盖（mock），无明显缺口
- `tests/e2e/` 已有 `test_e2e_maya_standalone.py`；`.github/workflows/e2e.yml` 已存在，多版本矩阵完备
- 后续方向：新增 Maya 功能域（如 XGen、Arnold AOV、bifrost）或深化 server.py 覆盖

---

## 2026-04-10 (Round 9 — server.py 100% coverage)

### Context
- Branch: `feat/skills-sop`
- Baseline: 875 tests passing (1 skipped), server.py at 90%

### Work done
1. **`tests/test_server_coverage.py`** — 11 new tests for `server.py`:
   - `TestCollectSkillSearchPathsCoverage` (4): builtin dir not-a-dir branch, get_skills_dir() default appended, no-duplicate guard, None guard
   - `TestRepeatingPollClosure` (3): executor.poll_pending() called, executor=None skip, recursive reschedule
   - `TestLoadSkillFailure` (2): warning logged + self returned, mixed success/failure counts
   - `TestStartServerExtraSkillPaths` (2): extra_skill_paths passed, register_builtins=False skips call
2. Fixed 3 test issues during development: WindowsPath.is_dir read-only → patch module attr; Rust builtin method no return_value → replace _server with MagicMock; unused imports/vars
3. All ruff E/W/F checks pass (0 errors)

### State after this round
- Tests: **886 passed, 1 skipped** (was 875)
- `server.py` coverage: **100%** (was 90%)
- `TOTAL` coverage: **100%**
- Committed: `ac245b7` on `feat/skills-sop`

### Remaining gaps for Round 10
- All source modules now at 100% coverage
- Next directions:
  - New Maya Skill domains: XGen, Arnold AOV, Bifrost, nParticles, MASH
  - `tests/e2e/` directory exists (`test_e2e_maya_standalone.py`) but only basic standalone test; expand per-skill E2E coverage
  - `.github/workflows/e2e.yml` already configured
  - Consider adding new Skill: `maya-xgen/` (XGen hair/fur operations)
  - Consider adding `maya-mash/` (MASH motion graphics)

---

## 2026-04-10 (Round 10 — maya-xgen, maya-mash, maya-selection new Skill domains)

### Context
- Branch: `feat/skills-sop`
- Baseline: 886 tests passing (1 skipped), all modules 100% coverage

### Work done
1. **New Skill: `maya-xgen`** — 5 scripts (create_description, list_descriptions, delete_description, set_xgen_attribute, get_xgen_attribute); wraps `xgenm` Python API
2. **New Skill: `maya-mash`** — 5 scripts (create_network, list_networks, delete_network, add_node, set_mash_attribute); wraps `MASH.api` Python API
3. **New Skill: `maya-selection`** — 5 scripts (grow_selection, shrink_selection, invert_selection, convert_selection, select_similar); uses `maya.cmds` selection utilities
4. **`tests/test_skills_round13.py`** — 64 new tests across 3 Skill groups; fixed MASH mock pattern: `sys.modules["MASH"].api = mock_mapi` + `sys.modules["MASH.api"] = mock_mapi` (both must be wired together for `import MASH.api as mapi` to route correctly)
5. ruff auto-fix: 5 unused import errors fixed

### State after this round
- Tests: **950 passed, 1 skipped** (was 886)
- All ruff checks pass (0 errors)
- Committed: `775ec44` on `feat/skills-sop`

### Remaining gaps for Round 11
- `maya-xgen`, `maya-mash`, `maya-selection` SKILL.md docs are minimal; could expand with more scripts (e.g. XGen preview export, MASH falloff, selection by UV shell)
- Arnold AOV / Bifrost / nParticles Skill domains not yet created
- `tests/e2e/` exists but only covers basic standalone; expand with xgen/mash/selection E2E
- Python 3.7 compat audit: no walrus/X|Y found in new scripts (all use str.format, not f-strings with complex exprs)

---

## 2026-04-10 (Round 11 — maya-arnold-aov and maya-bifrost new Skill domains)

### Context
- Branch: `feat/skills-sop`
- Baseline: 950 tests passing (1 skipped), all modules 100% coverage

### Work done
1. **New Skill: `maya-arnold-aov`** — 5 scripts:
   - `add_aov`: Create Arnold AOV node with auto-type inference (RGBA/RGB/FLOAT/VECTOR); connects to `defaultArnoldRenderOptions`
   - `list_aovs`: List all `aiAOV` nodes with name/type/enabled info
   - `delete_aov`: Find and delete AOV by `aiAOV.name` attribute
   - `set_aov_attribute`: Set any attribute on an AOV node (handles string vs numeric types)
   - `enable_aov`: Toggle AOV enabled/disabled state
2. **New Skill: `maya-bifrost`** — 5 scripts:
   - `create_bifrost_graph`: Create `bifrostGraph` node, auto-loads plugin if needed
   - `list_bifrost_graphs`: List all `bifrostGraph` nodes in scene
   - `add_bifrost_node`: Add Bifrost compound via `vnnCompound` MEL command; validates node type
   - `connect_bifrost_ports`: Wire ports via `vnnConnect`; validates all 5 required args
   - `set_bifrost_property`: Set port default value via `vnnNode`; serialises list → space-joined string
3. **`tests/test_skills_round14.py`** — 53 new tests; fixed `add_aov` AOV type lookup to handle case-sensitive keys (e.g. "Z" → FLOAT); fixed ruff F401 (removed unused `types` and `pytest` imports)
4. Bug fix: `add_aov` case-insensitive type lookup: check original case first, then lowercase, fallback to "RGB"

### State after this round
- Tests: **1003 passed, 1 skipped** (was 950)
- All ruff checks pass (0 errors)
- Committed: `51d0415` on `feat/skills-sop`
- Skill domains: 31 (added maya-arnold-aov, maya-bifrost)

### Remaining gaps for Round 12
- New domains not yet added: `maya-nparticles` (particle system), `maya-cache` (Alembic/Geometry cache), `maya-audio` (sound node control)
- `server.py` coverage remains 100% (no regression)
- Python 3.7 compat: all new scripts use `from __future__ import annotations` + `typing` module correctly
- `tests/e2e/` exists but could add arnold-aov and bifrost E2E stubs (Docker headless limitations apply)

---

## 2026-04-10 (Round 12 — maya-nparticles, maya-cache, maya-audio new Skill domains)

### Context
- Branch: `feat/skills-sop`
- Baseline: 1003 tests passing (1 skipped), all modules 100% coverage

### Work done
1. **New Skill: `maya-nparticles`** — 5 scripts:
   - `create_nparticle_system`: Create nParticle object with nucleus; supports points/spheres/sprites/streaks/blobby types
   - `list_nparticle_systems`: List all nParticle nodes with nucleus and particle count info
   - `set_nparticle_attribute`: Set scalar or vector attributes on nParticle nodes
   - `emit_particles`: Create and connect emitters (omni/directional/surface/curve/volume types)
   - `delete_nparticle_system`: Delete nParticle and optionally its nucleus solver
2. **New Skill: `maya-cache`** — 5 scripts:
   - `export_alembic`: Export objects to Alembic with frame range, world space, UV options
   - `import_alembic`: Import Alembic with namespace and fit-time-range support
   - `create_ncache`: Create nCache for nCloth/nParticle; uses `cmds.cacheFile`
   - `list_caches`: List cacheFile, cacheBlend, AlembicNode nodes
   - `delete_cache`: Delete cache node with optional best-effort disk file cleanup
3. **New Skill: `maya-audio`** — 5 scripts:
   - `import_audio`: Import wav/aif/mp3 file as sound node with offset support
   - `list_audio_nodes`: List all audio nodes with file path and offset
   - `set_audio_offset`: Set frame offset on a sound node
   - `set_active_audio`: Activate sound node on Maya time slider via MEL
   - `delete_audio_node`: Delete audio node with type validation
4. **`tests/test_skills_round15.py`** — 76 new tests (all pass); all ruff checks pass

### State after this round
- Tests: **1079 passed, 1 skipped** (was 1003)
- Skill domains: 34 (added maya-nparticles, maya-cache, maya-audio)
- All ruff checks pass (0 errors)
- Committed: `f8876dc` on `feat/skills-sop`

### Remaining gaps for Round 13
- New Skill domains not yet added: `maya-grooming` (XGen interactive grooming), `maya-muscle` (muscle system), `maya-fluid` (fluid containers)
- `maya-nparticles` could add: `set_goal`, `per_particle_expression`, `convert_to_polygons`
- `maya-cache` could add: GPU cache import/export
- Python 3.7 compat: all new scripts use `from __future__ import annotations` + `typing` module correctly

---

## 2026-04-10 (Round 13 — maya-grooming, maya-muscle, maya-fluid new Skill domains)

### Context
- Branch: `feat/skills-sop`
- Baseline: 1079 tests passing (1 skipped), all modules 100% coverage

### Work done
1. **New Skill: `maya-grooming`** — 5 scripts:
   - `create_groom`: Create XGen interactive groom description on a mesh (igCreateGroom)
   - `list_groomables`: List all igmGroom shapes in scene
   - `delete_groom`: Delete groom shape/transform
   - `convert_groom_to_curves`: Convert groom splines to NURBS curves via igConvertGroom
   - `export_groom_cache`: Export groom cache (.igc) via igExportGroom
2. **New Skill: `maya-muscle`** — 5 scripts:
   - `create_muscle_capsule`: Create cMuscleObject between two joints
   - `list_muscles`: List all cMuscleObject nodes
   - `delete_muscle`: Delete muscle capsule/transform
   - `set_muscle_attribute`: Set radius/squash/stretch/rest attrs via attributeQuery+setAttr
   - `attach_muscle_to_skin`: Attach muscle to cMuscleSystem deformer (with type validation)
3. **New Skill: `maya-fluid`** — 5 scripts:
   - `create_fluid_container`: Create 3D/2D fluid container with resolution/size params
   - `list_fluid_containers`: List fluidShape nodes with resolution and emitters
   - `delete_fluid_container`: Delete container + optional emitter cleanup
   - `set_fluid_attribute`: Set viscosity/buoyancy/dissipation etc.
   - `add_fluid_emitter`: Add omni/directional/volume emitter to existing container
4. **`tests/test_skills_round16.py`** — 81 new tests; all pass
5. All ruff E/W/F checks pass (0 errors)
6. Fixed server.py minor comment/attr drift (removed `_poll_job` attribute no longer needed)

### State after this round
- Tests: **1160 passed, 1 skipped** (was 1079)
- Skill domains: 37 (added maya-grooming, maya-muscle, maya-fluid)
- All ruff checks pass (0 errors)
- Committed: `9eb44cf` on `feat/skills-sop`

### Remaining gaps for Round 14
- New domains to consider: `maya-ocean` (ocean shader/waves), `maya-toon` (toon outline), `maya-paint-effects` (stroke brushes)
- `maya-grooming` could expand: import_groom_cache, set_groom_attribute, create_groom_modifier
- `maya-muscle` could expand: set_muscle_weights, list_muscle_systems, create_muscle_system
- `maya-fluid` could expand: export_fluid_cache, import_fluid_cache, set_fluid_color_ramp
- Python 3.7 compat: all new scripts use `from __future__ import annotations` + `typing` module — verified clean
- `tests/e2e/` exists but could add grooming/muscle/fluid E2E stubs

---

## 2026-04-10 (Round 14 — maya-ocean, maya-toon, maya-paint-effects new Skill domains)

### Context
- Branch: `feat/skills-sop`
- Baseline: 1160 tests passing (1 skipped), all modules 100% coverage

### Work done
1. **New Skill: `maya-ocean`** — 5 scripts:
   - `create_ocean`: Create ocean plane with oceanShader + shading group; sets waveHeight/waveTurbulence
   - `list_oceans`: List all oceanShader nodes with wave attrs
   - `delete_ocean`: Delete oceanShader + optionally connected geometry/SGs
   - `set_ocean_attribute`: Set scalar/vector attrs on oceanShader node
   - `create_wake`: Create oceanWake node driven by object/locator; auto-connects time attr
2. **New Skill: `maya-toon`** — 5 scripts:
   - `create_toon_outline`: Run `assignNewPfxToon` MEL on target objects; rename + set lineWidth
   - `list_toon_lines`: List all pfxToon nodes with profile/crease line width
   - `delete_toon_line`: Type-validate then delete pfxToon node
   - `set_toon_attribute`: Set scalar/color attrs on pfxToon nodes
   - `assign_toon_shader`: Create surfaceShader + SG, assign to objects for flat/toon look
3. **New Skill: `maya-paint-effects`** — 5 scripts:
   - `create_stroke`: Create Paint Effects stroke via MEL; optional brush_path sourcing
   - `list_strokes`: List all stroke nodes with transform and brush attrs
   - `delete_stroke`: Delete stroke transform (shape → parent lookup)
   - `set_brush_attribute`: Set scalar/color attrs on stroke nodes
   - `convert_stroke_to_poly`: Call `doPaintEffectsToPoly` MEL; return newly selected poly mesh
4. **`tests/test_skills_round17.py`** — 78 new tests; all pass; ruff 0 errors

### State after this round
- Tests: **1238 passed, 1 skipped** (was 1160)
- Skill domains: 40 (added maya-ocean, maya-toon, maya-paint-effects)
- All ruff checks pass (0 errors)
- Committed: `2150fef` on `feat/skills-sop`

### Remaining gaps for Round 15
- New Skill domains to consider: `maya-hdri` (IBL lighting), `maya-camera-sequence` (camera shot management), `maya-skinning-utils` (weight painting helpers)
- `maya-ocean` could expand: export_ocean_cache, set_ocean_foam, create_ocean_plane_preset
- `maya-toon` could expand: batch_assign_toon_outline, export_toon_render
- Python 3.7 compat: all new scripts use `from __future__ import annotations` + typing — verified clean

---

## 2026-04-10 (Round 15 — maya-hdri, maya-camera-sequence, maya-skinning-utils new Skill domains)

### Context
- Branch: `feat/skills-sop`
- Baseline: 1238 tests passing (1 skipped), all modules 100% coverage

### Work done
1. **New Skill: `maya-hdri`** — 5 scripts:
   - `create_sky_dome`: Create aiSkyDomeLight; auto-load mtoa plugin; optional HDRI file texture connection
   - `set_hdri_image`: Assign/replace HDRI file on existing sky dome (reuses existing file node)
   - `list_sky_domes`: List all aiSkyDomeLight nodes with exposure/intensity/hdri_path
   - `set_sky_dome_attribute`: Set any attribute (numeric/string/list) on sky dome shape
   - `delete_sky_dome`: Delete by shape or transform; optional file-node cleanup
2. **New Skill: `maya-camera-sequence`** — 5 scripts:
   - `create_shot`: Create shot node with camera, frame range and sequence timing
   - `list_shots`: List all shot nodes sorted by sequence_start
   - `set_shot_camera`: Reassign camera for an existing shot node
   - `delete_shot`: Delete a shot node (type-validated)
   - `set_shot_range`: Update start/end/sequence_start timing of a shot
3. **New Skill: `maya-skinning-utils`** — 5 scripts:
   - `copy_skin_weights`: Copy skin weights between meshes (surface/influence association options)
   - `normalize_skin_weights`: Set normalizeWeights mode + force-normalize via skinPercent
   - `prune_skin_weights`: Remove influences below threshold via skinPercent
   - `mirror_skin_weights`: Mirror weights across YZ/XY/XZ with optional inverse
   - `get_skin_info`: Query skinCluster influences, vertex count, max influences, normalize mode
4. **`tests/test_skills_round18.py`** — 86 new tests; all pass; ruff 0 errors
5. Fixed 2 test bugs: `TestSetShotRange` mock needed `side_effect` function (not list) to handle edit vs query calls separately

### State after this round
- Tests: **1316 passed, 1 skipped** (was 1238)
- Skill domains: 43 (added maya-hdri, maya-camera-sequence, maya-skinning-utils)
- All ruff checks pass (0 errors)
- Committed: `7a24dc2` on `feat/skills-sop`

### Remaining gaps for Round 16
- New Skill domains: `maya-mocap` (motion capture retargeting), `maya-cloth-sim` (nCloth extended), `maya-pose-library` (pose saving/loading)
- `maya-skinning-utils` could expand: `set_skin_weights` (direct per-vertex weight assignment), `add_influence`, `remove_influence`
- `maya-hdri` could expand: `set_sky_dome_rotation`, `list_ibl_nodes` (support aiPhysicalSky)
- Python 3.7 compat: all new scripts use `from __future__ import annotations` — verified clean

---

## 2026-04-10 (Round 5 — attributes/dynamics/rigging/cameras/constraints/display/lighting test coverage)

### Context
- Branch: `feat/skills-sop`
- Baseline: 430 tests passing (1 skipped)

### Work done
1. **Bug fix**: `maya-lighting/scripts/delete_light.py` — `error_result()` missing `error` 2nd arg; fixed
2. **`tests/test_skills_round6.py`** — 96 new tests:
   - `maya-attributes`: add_attribute (7), set_attribute (6), get_attribute (5), list_attributes (5), delete_attribute (5)
   - `maya-dynamics`: create_nucleus (5), create_ncloth (5), create_nrigid (5), create_dynamic_field (5), connect_field_to_objects (5), set_ncloth_attribute (5), set_nrigid_attribute (5), set_nucleus_attribute (5), list_ncloth_nodes (4), list_nrigid_nodes (3)
   - `maya-rigging` (remaining): set_ik_fk_blend (8), set_joint_limit (7), set_joint_orient (6)
3. **`tests/test_skills_round7.py`** — 71 new tests:
   - `maya-cameras`: create_camera (4), get_camera_info (4), list_all_cameras (3), set_active_camera (4), set_camera_attribute (5)
   - `maya-constraints`: add_constraint (6), list_constraints (3), remove_constraint (4), create_constraint_weighted (4)
   - `maya-display`: create_display_layer (5), delete_display_layer (5), list_display_layers (3), set_display_layer (3)
   - `maya-lighting`: create_light (5), delete_light (4), list_lights (3), set_light_attribute (6)

### State after this round
- Tests: **597 passed, 1 skipped** (was 430)
- All ruff checks pass (0 errors)
- Commits: `dee7550`, `59b9de9` on `feat/skills-sop`

### Remaining gaps for Round 6
- `tests/e2e/` + `.github/workflows/e2e.yml` — not yet created
- All Skill directories now have unit test coverage; main remaining gap is E2E (Docker + mayapy)

