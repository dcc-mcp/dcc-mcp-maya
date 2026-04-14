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

## 2026-04-12 (Round 24 — DccCapabilities module + get_frame_range skill)

### State before this round
- Branch: `main`
- Tests: 2906 passed, 6 skipped (2 failures: test_round41 port conflict with 8765)
- dcc-mcp-core: v0.12.7+, new APIs include DccCapabilities, ObjectTransform, SceneObject, FrameRange
- All skill dirs populated; api.py had scene_object_from_node, object_transform_from_node

### Work done

**1. Bug fix: test_skills_round41.py port conflict**
- `TestBindAndRegisterVersionAutoDetect::test_bind_and_register_auto_version_calls_about` + `*_uses_about_return` were using default port 8765 which was already in use on the dev machine
- Fixed: assigned unique ports 18822 and 18823

**2. New module: `src/dcc_mcp_maya/capabilities.py`**
- `maya_capabilities()` — factory returning `DccCapabilities(scene_manager=True, transform=True, hierarchy=True, selection=True, render_capture=True, snapshot=True, undo_redo=True, file_operations=True, has_embedded_python=True, progress_reporting=True, scene_info=True)`
- `MAYA_CAPABILITIES_DICT` — pre-computed plain dict (no dcc_mcp_core import needed)

**3. `server.py` — `MayaMcpServer.get_capabilities()` method**
- Returns `DccCapabilities` instance via `maya_capabilities()` factory
- Works before `start()` is called; no side effects

**4. `api.py` — added `maya_capabilities` to `__all__` + imported from capabilities.py**

**5. `__init__.py` — added `maya_capabilities` to imports and `__all__`**

**6. New skill: `maya-animation/scripts/get_frame_range.py`**
- `get_frame_range()` → returns `frame_range` dict with `start/end/fps/current`
- Maps Maya time unit strings (film=24, pal=25, ntsc=30, show=48, palf=50, ntscf=60) + custom `Xfps` parsing
- Uses `skill_entry` decorator, has `prompt=`

**7. `test_skills_round44.py` — 47 tests, all pass**:
- TestMayaCapabilitiesFactory (10): DccCapabilities type, all flag assertions
- TestMayaCapabilitiesDict (3): constant existence, key consistency
- TestServerGetCapabilities (5): get_capabilities() on server before/after start
- TestPublicReexports (5): importable from init/api, in __all__
- TestGetFrameRangeHappyPath (10): all fps units, schema keys, prompt
- TestGetFrameRangeEdgeCases (8): exception handling, all fps mappings
- TestGetFrameRangeStructural (6): file exists, main callable, no legacy run(params)

### State after this round
- Tests: 2953 passed (+47), 6 skipped, 0 failures
- ruff: All checks passed
- Committed: `e6f9c2a feat(capabilities): add DccCapabilities module, server.get_capabilities(), get_frame_range skill; fix test_round41 port conflict; add test_skills_round44 (47 tests)`
- Pushed: `origin/main` updated

### Next priorities
1. Investigate and fix Dependabot 2 moderate dev-dep vulnerabilities (needs user authorization)
2. Add `FrameRange` structured output to more skills (query_scene_time_info, get_session_info)
3. Add `SceneObject` structured output to list_objects / get_selection
4. Consider adding `get_scene_objects` skill returning List[SceneObject] for cross-DCC scene exchange


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


---

## 2026-04-11 (Round 16 — 44 cmds.objExists 迁移 + test_skills_round30)

### State before this round
- Branch: `feat/skill-api-improvements`
- Tests: 2046 passed, 27 skipped
- cmds.objExists: 142 处分布在 89 个文件

### Work done

**批量迁移 44 处 `cmds.objExists` → `validate_node_exists` / `batch_validate_nodes`**：

目标文件（8个，集中在 maya-scripting 目录）：
- `uv_ops.py`: 8 处 → validate_node_exists（含 for-loop / copy_uvs 情形）
- `vertex_color.py`: 5 处 → validate_node_exists（含 component vtx 检查）
- `deformer_advanced.py`: 5 处 list 模式 → batch_validate_nodes（cluster/lattice/wire/sculpt）
- `mesh_ops.py`: 7 处 → validate_node_exists（全部清零）
- `rigging.py`: 5 处 → validate_node_exists（含 conditional `if parent and` 模式）
- `dynamics.py`: 2 处 conditional nucleus → validate_node_exists（保留 mag_attr 属性探测）
- `animation.py`: 2 处 list 模式 → batch_validate_nodes
- `sets.py`: 2 处 list 模式 → batch_validate_nodes

**工具脚本**（4 个，已提交入库）：
- `tools/migrate_uv_ops.py` — 简单 objExists 替换
- `tools/migrate_batch_validate.py` — list 模式替换（MISSING_LINE regex）
- `tools/migrate_standard_objexists.py` — 标准单节点替换
- `tools/fix_broken_batch_migration.py` — 修复 regex 残留片段（dangling error call）

**修复的问题**：migrate_batch_validate.py 的 regex 仅替换了第一行，遗留了多行 skill_error 参数 → fix_broken_batch_migration.py 逐行修复 `return err…` 残留。

**test_skills_round30.py** — 36 个新测试，全部通过：
- TestRound30Structural (6): 无语法错误/无 raw objExists/import 完整/全局计数<100
- TestUvOpsValidation (3): missing object / success / no raw guard
- TestVertexColorValidation (3): same pattern
- TestDeformerAdvancedBatchValidation (4): batch_validate_nodes 行为/import
- TestMeshOpsValidation (5): 全部清零/import/3 函数 missing-node
- TestRiggingValidation (4): import/no raw guard/missing parent/set_driven_key
- TestDynamicsConditionalValidation (3): no nucleus guard/import/mag_attr probe preserved
- TestAnimationBatchValidation (2): import/no broken return err
- TestSetsBatchValidation (3): import/no broken return err/no raw guard
- TestGlobalObjExistsReduction (2): total<100/validate usage ≥170 files

### State after this round
- Tests: 2082 passed (+36), 27 skipped, 0 failures
- cmds.objExists: 142 → 98（减少 44 处）
- ruff: 通过（0 errors）
- Committed: `69ee591 refactor(skills): migrate 44 cmds.objExists guards to validate_node_exists/batch_validate_nodes; add test_skills_round30 (36 tests)`
- Pushed: `origin/feat/skill-api-improvements` updated



---

## 2026-04-11 (Round 17 — 18 cmds.objExists guards migrated + test_skills_round31)

### State before this round
- Branch: `feat/skill-api-improvements`
- Tests: 2082 passed, 1 skipped
- cmds.objExists remaining: 98 across 84 files

### Work done

**1. Analysis of remaining 98 cmds.objExists instances**:
- Attribute probes (node.attr): 3 — kept intentionally
- Positive checks (if cmds.objExists): 21 — kept (logic guards, not error returns)
- List comprehensions ([o for o if not cmds.objExists]): 37 — complex, future work
- Inline/conditional: 19 — kept

**2. tools/migrate_remaining_objexists.py** — new migration tool:
- Targets `if not cmds.objExists(VAR):` + `return ...` two-line patterns
- Skips api.py (validate_node_exists implementation), attribute probes (full_attr variables)
- 18 replacements across 16 files

**3. Files migrated** (18 guards → validate_node_exists):
- maya-mesh-ops: create_proxy_mesh, get_mesh_edge_info, get_poly_count, merge_vertices
- maya-pipeline: get_asset_metadata, tag_asset_metadata
- maya-rigging: blend_shape_add_target (2 guards: blend_shape + target_mesh nodes)
- maya-scripting: cameras, get_script_node, lighting
- maya-utility: list_node_connections
- maya-uv-ops: get_uv_shell_info
- maya-vertex-color: create_color_set, get_vertex_color (2 guards), remove_vertex_colors, set_vertex_color

**4. ruff fixes**:
- E402: noqa added to validate_node_exists imports in get_asset_metadata.py, tag_asset_metadata.py
- E741: renamed `l` → `line`/`ln` in test_skills_round30.py

**5. test_skills_round31.py** — 70 new tests, all pass:
- TestStructural (52): parametrized × 16 files × 3 checks (no raw guard, import present, no syntax error) + 1 global count < 85
- TestMeshOpsRound31 (4): missing node tests for 4 scripts
- TestVertexColorRound31 (6): missing node + success + vtx_index query
- TestRiggingRound31 (5): blend_shape + target_mesh guards, wrong type, invalid weight
- TestPipelineRound31 (2): missing node for get/tag asset metadata
- TestUvOpsRound31 (2): missing node + success with shell_count
- TestCamerasLightingRound31 (2): missing node for set_*_attribute

### State after this round
- Tests: 2152 passed (+70), 1 skipped, 0 failures
- cmds.objExists: 98 → 80 (18 migrated)
- ruff: All checks passed
- Committed: `06cbf40 refactor(skills): migrate 18 cmds.objExists guards to validate_node_exists; add test_skills_round31 (70 tests); fix ruff E741 in test_round30`
- Pushed: `origin/feat/skill-api-improvements` updated


---

## 2026-04-12 (Round 18 — 26 list-comp objExists migrated to batch_validate_nodes)

### State before this round
- Branch: `feat/skill-api-improvements`
- Tests: 2152 passed, 27 skipped
- cmds.objExists remaining: 80 (categorized: 29 list-comp, 17 positive-guard, 2 attr-probe, 32 other)

### Work done

**Migrated 26 list-comprehension `cmds.objExists` patterns → `batch_validate_nodes`**:

Target pattern:
```python
missing = [o for o in objects if not cmds.objExists(o)]
if missing:
    return skill_error(...)
```
→
```python
err = batch_validate_nodes(cmds, list(objects))
if err:
    return err
```

Files migrated (25 individual scripts + scene_utils.py which already had top-level import):
- maya-animation: bake_constraints, bake_simulation (2)
- maya-blend-shape-utils: create_blend_shape (1)
- maya-deformers: create_cluster, create_lattice, sculpt_deformer, wire_deformer×2 (5)
- maya-dynamics: connect_field_to_objects, create_dynamic_field (2)
- maya-gpu-cache: export_gpu_cache (1)
- maya-instancer: create_instancer (1)
- maya-render-layers: create_render_layer (1)
- maya-rig-utils: add_space_switch (1)
- maya-rigging: create_blend_shape (1)
- maya-scene-utils: align_objects (1)
- maya-scripting: display, render_layers, scene_utils, texture_bake (4)
- maya-sets: add_to_set, create_set (2)
- maya-texture-bake: bake_textures (1)
- maya-xform-utils: bake_transforms, freeze_transforms, reset_pivot (3)

**3 tools added** (to tools/): migrate_listcomp_objexists.py, fix_batch_validate_imports.py, fix_inline_batch_imports_to_top.py

**test_skills_round32.py** — 76 tests, all pass:
- TestRound32Structural (54): parametrized × 25 files × 2 checks + global count <60 + usage count >=35
- TestDeformersRound32 (7): create_cluster (missing/happy/empty), wire_deformer (missing curve/mesh), create_lattice/sculpt_deformer missing
- TestXFormUtilsRound32 (4): freeze_transforms (missing/happy), reset_pivot, bake_transforms missing
- TestAnimationRound32 (2), TestBlendShapeRound32 (1), TestDynamicsRound32 (2)
- TestGpuCacheRound32 (1), TestInstancerRound32 (1), TestRenderLayersRound32 (1)
- TestRigUtilsRound32 (1), TestSceneUtilsRound32 (1), TestSetsRound32 (2), TestTextureBakeRound32 (1)

**Key fix**: `_load_and_call` helper keeps `patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds})` active during both module load AND function call; `mock_maya.cmds = mock_cmds` ensures `import maya.cmds as cmds` gets the correct mock.

### State after this round
- Tests: 2228 passed (+76), 27 skipped, 0 failures
- cmds.objExists: 80 → 54 (26 migrated; 3 skipped: positive-filter patterns in clean_mocap_keys, sets.py×2)
- batch_validate_nodes usage: 39 scripts
- ruff: All checks passed
- Committed: `1c4f500 refactor(skills): migrate 26 list-comp cmds.objExists to batch_validate_nodes; add test_skills_round32 (76 tests)`
- Pushed: `origin/feat/skill-api-improvements` updated



---

## 2026-04-12 (Round 22 — Arnold fallback maya_warning 扩展)

### State before this round
- Branch: `main`
- Tests: 2851 passed, 6 skipped (100% coverage)
- Last commit: `4ce6850` (load_hdri Arnold fallback warning)
- All 64 SKILL.md have tools: arrays

### Work done

**Analysis**: Scanned remaining 55 cmds.objExists instances — all are legitimate:
- `continue` patterns in loops (skip missing objects, not error returns)
- Attribute probe fallback logic (`node.attr` format)
- Positive guards (check if attribute plug exists before set)
These are intentionally correct usage, no migration needed.

**1. create_hdri_dome.py — Arnold fallback emits maya_warning**:
- Added `from dcc_mcp_maya.api import maya_warning` import
- When `mtoa` plugin not loaded → `ambientLight` fallback now returns `maya_warning(...)` with `context["warning"]` = "Arnold (mtoa) was not available; used ambientLight as fallback."
- Arnold success path → `skill_success` (no warning)

**2. create_render_pass.py — Arnold renderer + mtoa not loaded → maya_warning**:
- Added `from dcc_mcp_maya.api import maya_warning` import
- Added `cmds.pluginInfo("mtoa", loaded=True, query=True)` check in Arnold renderer path
- mtoa not loaded → falls back to standard `renderPass` node + returns `maya_warning(...)`
- mtoa loaded → creates `aiAOV` node + `skill_success` (no warning)
- mayaSoftware renderer → standard `renderPass` node + `skill_success` (unchanged)

**3. test_skills_round42.py — 27 new tests, all pass**:
- TestCreateHdriDomeArnoldFallback (6): fallback success/warning/arnold-mention/dome_node/prompt/ambientLight
- TestCreateHdriDomeArnoldSuccess (3): success/no-warning/aiSkyDomeLight
- TestCreateHdriDomeStructural (3): import/call/fallback-node-type
- TestCreateRenderPassArnoldFallback (6): success/warning/arnold-mention/renderPass-not-aiAOV/renderer/prompt
- TestCreateRenderPassArnoldSuccess (3): success/no-warning/aiAOV
- TestCreateRenderPassMayaSoftware (3): success/no-warning/renderPass
- TestCreateRenderPassStructural (3): import/call/pluginInfo-check

### State after this round
- Tests: 2878 passed (+27), 6 skipped, 0 failures
- Coverage: 100% (unchanged)
- ruff: All checks passed
- Committed: `8f11f4b feat(api): emit maya_warning on Arnold fallback in create_hdri_dome and create_render_pass; add test_skills_round42 (27 tests)`
- Pushed: `origin/main` updated

---

## 2026-04-12 (Round 23 — mtoa plugin availability guards for maya-arnold-aov)

### State before this round
- Branch: `main`
- Tests: 2878 passed, 6 skipped
- dcc-mcp-core: v0.12.7 (stable, no breaking changes)
- 15 Arnold scripts missing pluginInfo checks; all 64 SKILL.md already have tools: arrays

### Work done

**Analysis**: Reviewed all 15 "Arnold scripts missing plugin check":
- `maya-arnold-aov` (5): All 5 scripts directly create/query `aiAOV` nodes — mtoa not loaded → RuntimeError. **Fixed.**
- `maya-hdri` (3 queries): Already gracefully handle node type detection; aiSkyDomeLight absent = empty result. No change needed.
- `maya-light-rig` (2): Arnold types in enum lists only; already handled gracefully. No change needed.
- `maya-lighting/list_lights.py`: Same — Arnold types in _LIGHT_SHAPE_TYPES list, cmds.ls returns [] gracefully. No change needed.
- `maya-render-passes` (3 queries): aiAOV already handled via cmds.ls(type="aiAOV") returning []. No change needed.
- `maya-scripting/utility.py`: Arnold types in get_scene_statistics light_types list only. No change needed.

**5 scripts modified** in `maya-arnold-aov`:
- `add_aov.py` — `skill_error` when mtoa not loaded (hard block: cannot create aiAOV)
- `list_aovs.py` — `skill_success` empty (graceful: return aovs=[], count=0 with helpful prompt)
- `enable_aov.py` — `skill_error` when mtoa not loaded
- `delete_aov.py` — `skill_error` when mtoa not loaded
- `set_aov_attribute.py` — `skill_error` when mtoa not loaded

**test_skills_round43.py — 28 new tests, all pass**:
- TestAddAovMtoaCheck (5): not-loaded error/solution/loaded-proceeds/empty-name-first/context
- TestListAovsMtoaCheck (5): not-loaded empty/message/prompt/loaded-queries-ls/loaded-with-aovs
- TestEnableAovMtoaCheck (4): not-loaded error/empty-name-first/loaded-not-found/loaded-success
- TestDeleteAovMtoaCheck (4): not-loaded error/empty-name-first/loaded-not-found/loaded-success
- TestSetAovAttributeMtoaCheck (6): not-loaded/empty-name/empty-attr/not-found/success/string-type
- TestAovScriptsStructural (3+1): pluginInfo in all scripts/mtoa in all scripts/add_aov uses skill_error/list_aovs uses skill_success

### State after this round
- Tests: 2906 passed (+28), 6 skipped, 0 failures
- ruff: All checks passed
- Committed: `b540188 feat(skills): add mtoa plugin availability guards to all 5 maya-arnold-aov scripts; add test_skills_round43 (28 tests)`
- Pushed: `origin/main` updated

### Next priorities
1. GitHub Dependabot 2 moderate vulnerabilities — need user authorization to bump dev deps
2. Investigate remaining Arnold-adjacent scripts for any other potential RuntimeError paths
3. Verify dcc-mcp-core FramedChannel.call v0.12.7 integration opportunities
4. Consider adding `aiPhotometricLight` / `aiMeshLight` pattern in list_lights to test coverage

---

## 2026-04-12 (Round 25 — server.py SkillCatalog API coverage)

### State before this round
- Branch: `main`
- Tests: 2953 passed, 6 skipped
- server.py already uses create_skill_manager, SkillCatalog, search_actions, get_categories, get_tags, bind_and_register, find_best_service, rank_services
- Missing: is_skill_loaded, get_skill_info methods; no tests for search_skills, unregister_skill, find_skills, get_skill_categories, get_skill_tags, rank_services, find_best_service

### Work done

**1. server.py — added 2 new SkillCatalog methods**:
- `is_skill_loaded(name)` — wraps `SkillCatalog.is_loaded`, returns bool, False on exception
- `get_skill_info(name)` — wraps `SkillCatalog.get_skill_info`, returns SkillMetadata or None on exception

**2. test_skills_round45.py — 48 new tests, all pass**:
- TestSearchSkills (7): category/dcc_name default/explicit/tags/registry-none/exception/no-attr
- TestUnregisterSkill (5): calls unregister/dcc_name forwarded/ignores exception/registry-none/no-attr
- TestFindSkills (4): list/forwards query-tags-dcc/exception/none-args
- TestGetSkillCategories (3): sorted-list/exception/registry-none
- TestGetSkillTags (5): list/default-dcc/explicit-dcc/exception/registry-none
- TestRankServices (4): list/default-maya/explicit-dcc/exception
- TestFindBestService (4): service/default-maya/explicit-dcc/none-on-exception
- TestIsSkillLoaded (5): true/false/forwarded/exception/truthy-coercion
- TestGetSkillInfo (5): metadata/none/forwarded/exception/description-accessible
- TestServerStructural (6): all new methods present, rank_services/find_best_service are @staticmethod

### State after this round
- Tests: 3001 passed (+48), 6 skipped, 0 failures
- ruff: All checks passed
- Committed: `401f0c4 feat(server): add is_skill_loaded, get_skill_info to MayaMcpServer; add test_skills_round45 (48 tests)`
- Pushed: `origin/main` updated

### Next priorities
1. GitHub Dependabot 2 moderate dev-dep vulnerabilities — need user authorization
2. `SandboxContext` integration: wrap skill execution in sandbox for safety
3. `InputValidator` integration: validate action parameters against schema before dispatch
4. Add `SkillSummary` structured return type hints to find_skills / list_skills results

---

## 2026-04-12 (Round 26 — InputValidator + ScriptResult + SceneStatistics integration)

### State before this round
- Branch: `feat/upgrade-dcc-mcp-core-0.12.17`
- Tests: 3001 passed, 6 skipped
- New APIs available: InputValidator, ScriptResult, ScriptLanguage, SceneInfo, SceneStatistics, SerializeFormat

### Work done

**1. api.py — 2 new helpers:**
- `make_input_validator(string_fields, number_fields, injected_fields)` — factory wrapping `dcc_mcp_core.InputValidator`; validates field presence and numeric ranges from a simple dict spec
- `validate_input(validator, params)` — serialises params to JSON and calls `InputValidator.validate(params_json)`; returns `(bool, err_msg|None)`; graceful on non-serialisable inputs
- Both added to `__all__` and re-exported from top-level `dcc_mcp_maya` package

**2. execute_mel.py — refactored:**
- Uses `make_input_validator(string_fields={"script": (1, 1_000_000)})` to guard missing/empty script field
- Added `execution_time_ms` timing via `time.time()`
- Added `script_result` context key: ScriptResult-compatible dict `{success, output, error, execution_time_ms, context}`

**3. execute_python.py — refactored:**
- Uses `make_input_validator(string_fields={"code": (1, 1_000_000)})` for field validation
- Added `_DANGEROUS_PATTERNS` list + `_check_injection(code)` guard blocking: `os.system`, `subprocess`, `__import__`, `eval(`, `exec(`, `open(`, `shutil.rmtree`, `os.remove`, `os.unlink`, `os.rmdir`, `importlib`
- Added `execution_time_ms` timing
- Added `script_result` context key (ScriptResult-compatible dict)

**4. get_scene_statistics.py — refactored:**
- Now queries `materials`, `lights`, `cameras`, `textures` via `cmds.ls()`
- Adds `scene_statistics` context key: SceneStatistics-compatible dict `{object_count, polygon_count, vertex_count, material_count, texture_count, light_count, camera_count}`
- All legacy keys preserved for backward compatibility

**5. test_skills_round46.py — 55 new tests, all pass:**
- TestMakeInputValidator (9): instance creation, required string, valid string, required number, out-of-range, valid number, no fields, reexport, __all__
- TestValidateInput (3): returns tuple, graceful on non-serialisable, empty string min length
- TestExecuteMelInputValidator (10): missing param, valid, script_result key, success flag, output, execution_time_ms, exception, None return, script key, whitespace
- TestExecutePythonInjectionGuard (14): os.system, subprocess, __import__, safe code, empty, whitespace, script_result, success flag, output match, timing, capture_output, exception, open, eval
- TestGetSceneStatisticsStructured (12): scene_statistics key, all 7 standard fields, legacy keys, include_memory=False, scene_file, prompt
- TestStructuralChecks (7): structural content/import checks

### State after this round
- Tests: 3056 passed (+55), 6 skipped, 0 failures
- ruff: All checks passed
- Committed: `8a10ef2 feat(api): add make_input_validator/validate_input helpers; add injection guard and ScriptResult to execute_mel/execute_python; add SceneStatistics to get_scene_statistics; add test_skills_round46 (55 tests)`
- Pushed: `origin/feat/upgrade-dcc-mcp-core-0.12.17` (new branch)

### Next priorities
1. `SandboxContext` + `SandboxPolicy` integration — wrap execute_python/execute_mel in sandbox
2. Extend InputValidator to more skills (e.g. create_object size params, render resolution)
3. `serialize_result` / `SerializeFormat` helper in api.py for MsgPack transport
4. GitHub Dependabot 2 moderate dev-dep vulnerabilities — need user authorization
