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

## 2026-04-08 (Round 2 — scene utility actions)

### State before this round
- Branch: `auto-improve` at `ed2010c`, rebased onto `origin/main` at `2b39f1f`
- Actions: 33 registered
- Tests: 163 passing, coverage 99%

### Work done
1. Fetched origin; `origin/main` had a new commit `2b39f1f` (fix release PAT)
2. Rebased `auto-improve` onto `origin/main` (5 commits rebased cleanly)
3. Added 6 new scene utility actions to `scene.py`:
   - `duplicate_object(object_name, new_name=None, instance=False)` — duplicate with optional rename/instance
   - `freeze_transforms(object_name)` — bake transforms via `makeIdentity`
   - `center_pivot(object_name)` — center pivot via `xform(centerPivots=True)`
   - `get_bounding_box(object_name)` — query world bbox, return min/max/center/size
   - `set_visibility(object_name, visible)` — show/hide via `.visibility` attr
   - `lock_object(object_name, lock=True)` — lock/unlock 9 transform attrs
4. Registered all 6 in `actions/__init__.py` → total 39 actions
5. Added 29 new tests in `test_actions_extended.py`:
   - `TestDuplicateObject` (6 tests)
   - `TestFreezeTransforms` (4 tests)
   - `TestCenterPivot` (4 tests)
   - `TestGetBoundingBox` (4 tests)
   - `TestSetVisibility` (5 tests)
   - `TestLockObject` (5 tests)
   - `TestRegisterAllWithNewActions` (1 test, asserts >= 39)

### State after this round
- Tests: 192 passing (all pass), 0 failures
- Coverage: 99% total (scene.py 100%, all action modules 100%, server.py 91%)
- Committed: `1dc4968 feat(skills): add duplicate_object, freeze_transforms, center_pivot, get_bounding_box, set_visibility, lock_object scene actions`
- Pushed: `origin/auto-improve` force-with-lease updated

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Potential next actions to consider:
  - `get_scene_info` (detailed DAG hierarchy with parent/children info)
  - `export_scene` — export entire scene to FBX/OBJ
  - `set_frame_rate` — change scene FPS setting
  - `list_cameras` — list all cameras with their attributes
  - `create_joint` — create a joint/bone for rigging
  - `create_locator` — create a locator node
  - `create_curve` — create a NURBS curve
  - More animation: `delete_keyframes`, `copy_keyframes`, `bake_simulation`

---

## 2026-04-08 (Round 3 — rigging, DAG info, scene utilities)

### State before this round
- Branch: `auto-improve` at `1dc4968`, origin/main unchanged
- Actions: 39 registered
- Tests: 192 passing, coverage 99%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Added 5 new scene actions to `scene.py`:
   - `get_scene_info(include_transforms)` — full DAG transform hierarchy with parent/children/translate/rotate/scale
   - `export_scene(file_path, file_type)` — export entire scene (rename + save)
   - `set_frame_rate(fps)` — change scene FPS with validated fps string
   - `list_cameras(include_default)` — list all camera nodes with focal_length/clips/renderable
   - `create_locator(name, position)` — create spaceLocator with optional position
3. Created `src/dcc_mcp_maya/actions/rigging.py` with 2 new actions:
   - `create_joint(name, position, parent)` — skeletal joint creation with parent hierarchy
   - `create_curve(points, name, degree, periodic)` — NURBS curve creation
4. Registered all 7 new actions in `actions/__init__.py` → total 46 actions
5. Created `tests/test_actions_scene_extra.py` with 41 tests:
   - `TestGetSceneInfo` (5), `TestExportScene` (3), `TestSetFrameRate` (4), `TestListCameras` (4), `TestCreateLocator` (5)
   - `TestCreateJoint` (6), `TestCreateCurve` (6), `TestRegisterAllRound3` (2), `TestImportErrorBranches` (6)

### State after this round
- Tests: 233 passing (all pass), 0 failures
- Coverage: 99% total (rigging.py 100%, scene.py 99%, server.py 91% — Maya-only lines)
- Committed: `825bb43 feat(skills): add get_scene_info, export_scene, set_frame_rate, list_cameras, create_locator, create_joint, create_curve actions`
- Pushed: `origin/auto-improve` updated (1dc4968..825bb43)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- `scene.py` lines 609-611 — `except Exception` in `get_scene_info`, unreachable from mock environment
- Next action candidates:
  - `delete_keyframes(object_name, attributes, start_frame, end_frame)` — remove keyframe range
  - `bake_simulation(objects, start_frame, end_frame)` — bake simulation to keyframes
  - `set_joint_orient(joint_name, orient)` — set joint orientation for rigging
  - `mirror_joints(joint_name)` — mirror joint chain
  - `create_ik_handle(start_joint, end_joint)` — create IK handle
  - `assign_deformer(object_name, deformer_type)` — apply blend shape / cluster / skin cluster
  - `get_dag_path(object_name)` — return full DAG path for API usage

---

## 2026-04-08 (Round 4 — animation & rigging expansion)

### State before this round
- Branch: `auto-improve` at `825bb43`, rebased onto `origin/main` at `fe2de14` (chore: update github artifact actions)
- Actions: 46 registered
- Tests: 233 passing, coverage 99%

### Work done
1. Fetched origin; `origin/main` had a new commit `fe2de14` (update github artifact actions)
2. Rebased `auto-improve` onto `origin/main` (7 commits rebased cleanly)
3. Added 2 new animation actions to `animation.py`:
   - `delete_keyframes(object_name, attributes, start_frame, end_frame)` — delete keyframes via `cmds.cutKey`, supports range + attribute filter
   - `bake_simulation(objects, start_frame, end_frame, sample_by)` — bake simulation/constraints to keyframes via `cmds.bakeSimulation`
4. Added 3 new rigging actions to `rigging.py`:
   - `set_joint_orient(joint_name, orient, zero_scale_orient)` — set jointOrientX/Y/Z attrs with type validation
   - `mirror_joints(joint_name, mirror_behavior, search_replace, mirror_axis)` — mirror joint chain via `cmds.mirrorJoint`, supports YZ/XY/XZ
   - `create_ik_handle(start_joint, end_joint, solver, name)` — create IK handle via `cmds.ikHandle`, supports RP and SC solvers
5. Registered all 5 new actions in `actions/__init__.py` → total 51 actions
6. Created `tests/test_actions_rigging_anim.py` with 41 tests:
   - `TestDeleteKeyframes` (8), `TestBakeSimulation` (7), `TestSetJointOrient` (7), `TestMirrorJoints` (9), `TestCreateIkHandle` (8), `TestRegisterAllRound4` (2)

### State after this round
- Tests: 274 passing (all pass), 0 failures
- Coverage: 99% total (rigging.py 100%, animation.py 100%, scene.py 99%, server.py 91% — Maya-only lines)
- Committed: `dc7d9d7 feat(skills): add delete_keyframes, bake_simulation, set_joint_orient, mirror_joints, create_ik_handle actions`
- Pushed: `origin/auto-improve` force-with-lease updated (825bb43..dc7d9d7)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- `scene.py` lines 609-611 — `except Exception` in `get_scene_info`
- Next action candidates:
  - `assign_deformer(object_name, deformer_type)` — apply blend shape / cluster / skin cluster
  - `get_dag_path(object_name)` — return full DAG path
  - `set_joint_limit(joint_name, axis, min_angle, max_angle)` — joint rotation limits for rigging
  - `create_blend_shape(base_mesh, target_meshes)` — create blend shape deformer
  - `skin_cluster_bind(joints, mesh)` — bind skin cluster
  - `get_attribute(object_name, attribute)` — generic attribute getter
  - `set_attribute(object_name, attribute, value)` — generic attribute setter

---

## 2026-04-08 (Round 5 — deformer actions & generic attribute ops)

### State before this round
- Branch: `auto-improve` at `dc7d9d7`, rebased onto `origin/main` at `6b90561` (setup-python v6)
- Actions: 51 registered
- Tests: 274 passing, coverage 99%

### Work done
1. Fetched origin; `origin/main` had `6b90561` (chore: update actions/setup-python to v6)
2. Rebased `auto-improve` onto `origin/main` (8 commits rebased cleanly)
3. Added 3 deformer actions to `rigging.py`:
   - `assign_deformer(object_name, deformer_type)` — cluster/lattice/nonLinear/blendShape/wrap
   - `create_blend_shape(base_mesh, target_meshes, name, origin)` — blend shape deformer
   - `skin_cluster_bind(joints, mesh, max_influences, bind_method, name)` — skin cluster binding
4. Created new `actions/attributes.py` with 2 generic attribute actions:
   - `get_attribute(object_name, attribute)` — get any Maya node attribute, normalises compound tuples
   - `set_attribute(object_name, attribute, value, force)` — set scalar/vector/string attrs, handles locked attrs
5. Registered all 5 new actions in `actions/__init__.py` → total **56 actions**
6. Created `tests/test_actions_deformer_attrs.py` with 41 tests:
   - `TestAssignDeformer` (8), `TestCreateBlendShape` (7), `TestSkinClusterBind` (8)
   - `TestGetAttribute` (7), `TestSetAttribute` (9), `TestRegisterAllRound5` (2)

### State after this round
- Tests: **315 passing** (all pass), 0 failures
- Coverage: 99% total (attributes.py 100%, rigging.py 100%, scene.py 99%, server.py 91%)
- Committed: `5ee3d3b feat(skills): add assign_deformer, create_blend_shape, skin_cluster_bind, get_attribute, set_attribute actions`
- Pushed: `origin/auto-improve` force-with-lease updated (dc7d9d7..5ee3d3b)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- `scene.py` lines 609-611 — `except Exception` in `get_scene_info`
- Next action candidates:
  - `get_dag_path(object_name)` — return full DAG path for API usage
  - `set_joint_limit(joint_name, axis, min_angle, max_angle)` — joint rotation limits
  - `add_constraint(source, target, constraint_type)` — point/orient/parent/scale constraint
  - `disconnect_attr(source_attr, dest_attr)` — disconnect attribute connections
  - `connect_attr(source_attr, dest_attr)` — connect two node attributes
  - `list_connections(object_name, attribute)` — list connected nodes/attributes
  - `apply_symmetry(object_name, axis)` — apply mesh symmetry
  - `smooth_mesh(object_name, divisions)` — add smooth mesh preview or subdivision



---

## 2026-04-09 (Round 7 — construction history, symmetry, joint limits, expressions)

### State before this round
- Branch: `auto-improve` at `ecf27c5`, origin/main unchanged at `6b90561`
- Actions: 64 registered
- Tests: 371 passing, coverage 98%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Added 3 new actions to `node_graph.py`:
   - `list_history(object_name, future, levels)` — list construction history nodes with type info
   - `delete_history(object_name)` — delete construction history via `cmds.delete(constructionHistory=True)`
   - `apply_symmetry(object_name, axis, world_space)` — enable/disable mesh symmetry via `cmds.symmetricModelling`
3. Added 1 new action to `rigging.py`:
   - `set_joint_limit(joint_name, axis, min_angle, max_angle, enable)` — set rotation limits on joint X/Y/Z axis
4. Created new `actions/expressions.py` with 3 actions:
   - `create_expression(expression, name, object_name, attribute, unit_conversion)` — create Maya expression node
   - `list_expressions(object_name)` — list all expression nodes, optional filter by object
   - `delete_expression(expression_name)` — delete expression node by name
5. Registered all 7 new actions in `actions/__init__.py` → total **71 actions**
6. Created `tests/test_actions_history_expr.py` with 58 tests using autouse monkeypatch pattern:
   - `TestListHistory` (8), `TestDeleteHistory` (5), `TestApplySymmetry` (10)
   - `TestSetJointLimit` (10), `TestCreateExpression` (10), `TestListExpressions` (7), `TestDeleteExpression` (6), `TestRegisterAllRound7` (2)

### State after this round
- Tests: **429 passing** (all pass), 0 failures
- Coverage: 98%+ (new modules fully covered)
- Committed: `baaffd1 feat(skills): add list_history, delete_history, apply_symmetry, set_joint_limit, create_expression, list_expressions, delete_expression actions`
- Pushed: `origin/auto-improve` updated (ecf27c5..baaffd1)

---

## 2026-04-09 (Round 8 — display layers, pivot, alignment, annotation, transfer)

### State before this round
- Branch: `auto-improve` at `baaffd1`, origin/main unchanged at `6b90561`
- Actions: 71 registered
- Tests: 429 passing, coverage 98%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Created `actions/display.py` with 4 display layer actions:
   - `create_display_layer(name, objects, visible, display_type)` — create and populate a display layer
   - `set_display_layer(object_name, layer_name)` — assign object to existing display layer
   - `delete_display_layer(layer_name, remove_objects)` — delete layer (with optional member deletion)
   - `list_display_layers()` — list all layers with visibility/type/member_count
3. Created `actions/scene_utils.py` with 3 scene utility actions:
   - `set_pivot(object_name, position, pivot_type, world_space)` — set rotate/scale pivot explicitly
   - `align_objects(objects, axis, mode, reference)` — align objects along world axis (min/center/max)
   - `create_annotation(object_name, text, position)` — create viewport annotation label
4. Added `transfer_attributes(source, target, sample_space, ...)` to `node_graph.py`
5. Registered all 8 new actions in `actions/__init__.py` → total **79 actions**
6. Created `tests/test_actions_display_sceneutils.py` with 57 tests:
   - `TestCreateDisplayLayer` (8), `TestSetDisplayLayer` (5), `TestDeleteDisplayLayer` (6), `TestListDisplayLayers` (3)
   - `TestSetPivot` (8), `TestAlignObjects` (10), `TestCreateAnnotation` (7)
   - `TestTransferAttributes` (8), `TestRegisterAllRound8` (2)

### State after this round
- Tests: **486 passing** (all pass), 0 failures
- Coverage: 98%+ (new modules fully covered)
- Committed: `174ca75 feat(skills): add display layers, set_pivot, align_objects, create_annotation, transfer_attributes actions`
- Pushed: `origin/auto-improve` updated (baaffd1..174ca75)

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Created `actions/sets.py` with 4 object set actions:
   - `create_set(name, objects)` — create objectSet node with optional initial members
   - `add_to_set(set_name, objects)` — add objects to existing objectSet with type validation
   - `remove_from_set(set_name, objects)` — remove objects, skipping non-existent gracefully
   - `list_sets(include_internal)` — list all objectSet nodes, filtering built-in sets by default
3. Created `actions/references.py` with 3 file reference actions:
   - `create_reference(file_path, namespace, group_reference)` — cmds.file reference with namespace resolution
   - `list_references()` — list reference nodes, filtering sharedReferenceNode, graceful query failures
   - `remove_reference(reference_node, remove_namespace)` — remove ref + optional namespace cleanup
4. Created `actions/render_layers.py` with 3 render layer actions:
   - `create_render_layer(name, objects, make_current)` — legacy renderLayer with optional population
   - `set_render_layer(object_name, layer_name)` — assign to renderLayer with type validation
   - `list_render_layers(include_default)` — list layers with renderable/member_count/is_current
5. Registered all 10 new actions in `actions/__init__.py` → total **89 actions**
6. Created `tests/test_actions_sets_refs_layers.py` with 58 tests:
   - `TestCreateSet` (6), `TestAddToSet` (6), `TestRemoveFromSet` (6), `TestListSets` (5)
   - `TestCreateReference` (6), `TestListReferences` (5), `TestRemoveReference` (6)
   - `TestCreateRenderLayer` (6), `TestSetRenderLayer` (5), `TestListRenderLayers` (5)
   - `TestRegisterAllRound9` (2)

### State after this round
- Tests: **544 passing** (all pass), 0 failures
- Coverage: 98%+ (new modules fully covered)
- Committed: `b4d9711 feat(skills): add create_set, add_to_set, remove_from_set, list_sets, create_reference, list_references, remove_reference, create_render_layer, set_render_layer, list_render_layers actions`
- Pushed: `origin/auto-improve` updated (174ca75..b4d9711)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `get_shader_assignment(object_name)` — query which shader is on object/face
  - `reset_default_material(object_name)` — assign Lambert1 to object
  - `reload_reference(reference_node)` — reload an unloaded reference
  - `unload_reference(reference_node)` — unload reference without removing it
  - `list_namespaces()` — list all namespaces in the scene
  - `delete_render_layer(layer_name)` — delete a render layer
  - `set_render_layer_attribute(layer_name, attribute, value)` — set per-layer override
  - `create_utility_node(node_type, name)` — create any Maya utility/shading node
  - `get_scene_statistics()` — polygon count, texture memory, etc.

---

## 2026-04-09 (Round 10 — references, render layers, materials & utility)

### State before this round
- Branch: `auto-improve` at `b4d9711`, origin/main unchanged at `6b90561`
- Actions: 89 registered
- Tests: 544 passing, coverage 98%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Extended `references.py` with 3 new actions:
   - `reload_reference(reference_node)` — reload unloaded ref via `cmds.file(loadReference=...)`
   - `unload_reference(reference_node)` — unload ref without removing via `cmds.file(unloadReference=...)`
   - `list_namespaces(root_only)` — list namespaces, filtering built-in UI/shared
3. Extended `render_layers.py` with 2 new actions:
   - `delete_render_layer(layer_name)` — delete layer (protects defaultRenderLayer, auto-switches current)
   - `set_render_layer_attribute(layer_name, attribute, value)` — set scalar/triple/bool attr override
4. Extended `materials.py` with 2 new actions:
   - `get_shader_assignment(object_name)` — query shading groups via shape connections, deduplicates SGs
   - `reset_to_default_material(object_name)` — assign initialShadingGroup (lambert1) to object
5. Created new `actions/utility.py` with 2 new actions:
   - `create_utility_node(node_type, name)` — generic Maya utility/shading node factory
   - `get_scene_statistics()` — query polygon count, node count, camera/light/texture counts
6. Registered all 9 new actions in `actions/__init__.py` → total **98 actions**
7. Created `tests/test_actions_round10.py` with 56 tests (all passing)

### State after this round
- Tests: **600 passing** (all pass), 0 failures
- Coverage: 98% total (utility.py 100%, materials.py 100%, server.py 91% — Maya-only lines)
- Committed: `c5c9a55 feat(skills): add reload_reference, unload_reference, list_namespaces, delete_render_layer, set_render_layer_attribute, get_shader_assignment, reset_to_default_material, create_utility_node, get_scene_statistics actions`
- Pushed: `origin/auto-improve` updated (b4d9711..c5c9a55)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `set_namespace(object_name, namespace)` — move objects to a namespace
  - `rename_namespace(old_name, new_name)` — rename a namespace
  - `list_shadinggroups()` — list all shading engine nodes
  - `get_material_connections(material_name)` — list all texture/node connections into a material
  - `bake_textures(objects, file_path, resolution)` — bake lighting/AO to texture
  - `add_attribute(object_name, long_name, attr_type, default_value)` — add custom attr to node
  - `delete_attribute(object_name, attribute)` — remove custom attr
  - `list_attributes(object_name, user_defined)` — list attributes on a node


---

## 2026-04-09 (Round 11 — custom node attrs, namespace management, material network)

### State before this round
- Branch: `auto-improve` at `c5c9a55`, origin/main unchanged at `6b90561`
- Actions: 98 registered
- Tests: 600 passing, coverage 98%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Created `actions/node_attrs.py` with 3 custom attribute actions:
   - `add_attribute(object_name, long_name, attr_type, ...)` — add scalar/string/vector user-defined attrs
   - `delete_attribute(object_name, attribute)` — delete user-defined attrs only (rejects built-ins)
   - `list_attributes(object_name, user_defined, keyable, scalar_only)` — list attrs with type/value/keyable/locked info
3. Created `actions/namespaces.py` with 3 namespace lifecycle actions:
   - `set_namespace(object_name, namespace, create_if_missing)` — move object into namespace
   - `rename_namespace(old_name, new_name)` — rename namespace, protects UI/shared
   - `delete_namespace(namespace, merge_with_root)` — delete namespace with optional member merge
4. Extended `materials.py` with 2 new actions:
   - `get_material_connections(material_name)` — list all nodes connected into a material (textures, utilities)
   - `list_shading_groups()` — list all shadingEngine nodes with surface_shader/shader_type/member_count
5. Registered all 8 new actions in `actions/__init__.py` → total **106 actions**
6. Created `tests/test_actions_round11.py` with 49 tests (all passing):
   - `TestAddAttribute` (9), `TestDeleteAttribute` (5), `TestListAttributes` (5)
   - `TestSetNamespace` (6), `TestRenameNamespace` (6), `TestDeleteNamespace` (6)
   - `TestGetMaterialConnections` (5), `TestListShadingGroups` (5), `TestRegisterAllRound11` (2)

### State after this round
- Tests: **649 passing** (all pass), 0 failures
- Coverage: 98% total (node_attrs.py 100%, namespaces.py 100%, materials.py 100%)
- Committed: `0e34631 feat(skills): add add_attribute, delete_attribute, list_attributes, set_namespace, rename_namespace, delete_namespace, get_material_connections, list_shading_groups actions`
- Pushed: `origin/auto-improve` updated (c5c9a55..0e34631)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `bake_textures(objects, file_path, resolution)` — bake lighting/AO to texture
  - `set_color_management(color_space, rendering_space)` — configure scene color management
  - `create_camera(name, focal_length, fov_type)` — create a camera with settings
  - `set_camera_attribute(camera_name, attribute, value)` — modify camera focal/clip/renderable
  - `get_poly_count(object_name)` — query per-object polygon stats
  - `apply_subdivision(object_name, level)` — apply OpenSubdiv subdivision
  - `create_light(light_type, name, intensity, color)` — create point/spot/directional/area light
  - `set_light_attribute(light_name, attribute, value)` — modify light intensity/color/angle


### State before this round
- Branch: `auto-improve` at `174ca75`, origin/main unchanged at `6b90561`
- Actions: 79 registered
- Tests: 486 passing, coverage 98%
   - `add_constraint(source, target, constraint_type, maintain_offset, name)` — parent/point/orient/scale/aim constraints
   - `remove_constraint(target, constraint_type)` — remove constraints by type or all
   - `list_constraints(target)` — list all constraints on a node with type info
3. Created `actions/node_graph.py` with 5 new actions:
   - `connect_attr(source_attr, dest_attr, force)` — connect two Maya node attributes
   - `disconnect_attr(source_attr, dest_attr)` — disconnect with isConnected pre-check
   - `list_connections(object_name, attribute, incoming, outgoing)` — list connection pairs
   - `get_dag_path(object_name)` — resolve full DAG path via `cmds.ls(long=True)`
   - `smooth_mesh(object_name, divisions, method)` — "preview" (displaySmoothMesh) or "subdivide" (polySmooth)
4. Registered all 8 new actions in `actions/__init__.py` → total **64 actions**
5. Created `tests/test_actions_constraints_nodegraph.py` with 56 tests including ImportError branches

### State after this round
- Tests: **371 passing** (all pass), 0 failures
- Coverage: 98% total (constraints.py 90%, node_graph.py 95%, server.py 91%)
- Committed: `ecf27c5 feat(skills): add add_constraint, remove_constraint, list_constraints, connect_attr, disconnect_attr, list_connections, get_dag_path, smooth_mesh actions`
- Pushed: `origin/auto-improve` updated (5ee3d3b..ecf27c5)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `set_joint_limit(joint_name, axis, min_angle, max_angle)` — joint rotation limits
  - `list_history(object_name, future)` — list construction history nodes
  - `delete_history(object_name)` — delete construction history
  - `transfer_attributes(source, target, sample_space)` — transfer UVs/normals/colors
  - `create_expression(node, attribute, expression)` — set Maya expression on attribute
  - `apply_symmetry(object_name, axis)` — apply mesh symmetry






---

## 2026-04-09 (Round 20 — nCloth/nRigid, render quality/stats, transform space)

### State before this round
- Branch: `auto-improve` at `4a263fd`, origin/main unchanged at `6b90561`
- Actions: 178 (`__all__`)
- Tests: 1127 passing, coverage 95%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Extended `dynamics.py` with 2 new nDynamics actions:
   - `create_ncloth(mesh, nucleus, name)` — create nCloth dynamic cloth node on polygon mesh, optional nucleus connection
   - `create_nrigid(mesh, nucleus, name)` — create passive nRigid collider on polygon mesh, optional nucleus connection
3. Extended `render.py` with 2 new render actions:
   - `set_render_quality(preset)` — apply low/medium/high preset to defaultRenderQuality node (AA, shading samples, ray depth)
   - `get_scene_render_stats()` — query renderer/resolution/frame-range/output-prefix/quality summary
4. Extended `transforms.py` with 1 new action:
   - `set_transform_space(object_name, space, translate, rotate)` — set translate/rotate in world/local/parent/object space via `cmds.xform`
5. Updated `actions/__init__.py` → total **183 in `__all__`**, registered in `_ACTIONS`
6. Created `tests/test_actions_round20.py` with 44 tests (all passing):
   - `TestCreateNcloth` (8), `TestCreateNrigid` (8), `TestSetRenderQuality` (8)
   - `TestGetSceneRenderStats` (6), `TestSetTransformSpace` (12), `TestRegisterAllRound20` (2)

### State after this round
- Tests: **1171 passing** (all pass), 0 failures
- `__all__` actions: 183
- Committed: `44a6297 feat(skills): add create_ncloth, create_nrigid, set_render_quality, get_scene_render_stats, set_transform_space actions`
- Pushed: `origin/auto-improve` updated (4a263fd..44a6297)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `set_ncloth_attribute(ncloth_node, attribute, value)` — set nCloth node attribute
  - `set_nrigid_attribute(nrigid_node, attribute, value)` — set nRigid collider attribute
  - `list_ncloth_nodes()` — list all nCloth nodes in scene
  - `get_render_pass_list()` — list all render passes defined in the scene
  - `create_render_pass(name, pass_type)` — create a render pass for AOV
  - `add_post_process(process_type, output_path)` — add render post-process operation
  - `set_shading_mode(mode)` — set viewport shading mode (wireframe/smooth/textured)
  - `get_mesh_edge_info(object_name, edge_index)` — query edge length/connected vertices
  - `select_by_material(material_name)` — select all objects with a given material
  - `create_proxy_mesh(object_name, reduction)` — create a simplified proxy mesh


### State before this round
- Branch: `auto-improve` at `19bbc6f`, origin/main unchanged at `6b90561`
- Actions: 172 (`__all__`)
- Tests: 1081 passing, coverage 95%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Extended `deformer_advanced.py` with 2 new actions:
   - `wire_deformer(curves, objects, name, dropoff_distance)` — wire deformer along NURBS curves via `cmds.wire`
   - `sculpt_deformer(objects, name, mode, max_displacement)` — sculpt deformer (stretch/project/flip) via `cmds.sculpt`
3. Created `actions/dynamics.py` with 4 new nDynamics actions:
   - `create_nucleus(name, gravity, wind_speed, wind_direction)` — create nucleus solver, connect to time node
   - `set_nucleus_attribute(nucleus, attribute, value)` — set scalar/triple/string attrs with type validation
   - `create_dynamic_field(field_type, name, magnitude, objects)` — gravity/turbulence/radial/uniform/vortex/drag/newton/air field
   - `connect_field_to_objects(field_node, objects)` — wire field to dynamic objects via `cmds.connectDynamic`
4. Registered all 6 new actions in `actions/__init__.py` → total **178 in `__all__`**, **174 in `_ACTIONS`**
5. Created `tests/test_actions_round19.py` with 46 tests (all passing):
   - `TestWireDeformer` (7), `TestSculptDeformer` (9)
   - `TestCreateNucleus` (7), `TestSetNucleusAttribute` (6)
   - `TestCreateDynamicField` (9), `TestConnectFieldToObjects` (5)
   - `TestRegisterAllRound19` (2)

### State after this round
- Tests: **1127 passing** (all pass), 0 failures
- `__all__` actions: 178
- Committed: `4a263fd feat(skills): add wire_deformer, sculpt_deformer, create_nucleus, set_nucleus_attribute, create_dynamic_field, connect_field_to_objects actions`
- Pushed: `origin/auto-improve` updated (19bbc6f..4a263fd)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `set_render_quality(quality_preset)` — high/medium/low quick render quality preset
  - `add_dynamic_attribute(particle_system, attr_name, type)` — add per-particle runtime attribute
  - `get_particle_count(particle_system)` — fast particle count query
  - `create_ncloth(mesh, nucleus)` — create nCloth node on a mesh
  - `create_nrigid(mesh, nucleus)` — create passive nRigid collider
  - `set_paint_effects(stroke_name, attribute, value)` — paint effects stroke attribute
  - `create_paint_effects_stroke(brush_path, path_curve)` — attach paint effects brush to curve
  - `get_scene_render_stats()` — query renderer, render globals settings summary
  - `set_transform_space(object_name, space)` — set object space (world/local/parent)


### State before this round
- Branch: `auto-improve` at `b666f55`, origin/main unchanged at `6b90561`
- Actions: 162 registered (`__all__`)
- Tests: 1024 passing, coverage 95%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Added 3 new animation actions to `animation.py`:
   - `export_animation_curves(object_name, file_path, attributes, start_frame, end_frame)` — export animCurve nodes to Maya ASCII/Binary file
   - `import_animation_curves(file_path, target_object, merge)` — import anim curves and optionally retarget to an object
   - `query_scene_time_info()` — single-call snapshot of FPS, anim range, playback range, current time
3. Created `actions/particles.py` with 4 new actions:
   - `create_particle_system(name, particle_count, position, use_nparticle)` — classic or nParticle system
   - `get_particle_system_info(particle_system)` — query node_type/count/lifeMode/radius/conserve/nucleus
   - `set_particle_attribute(particle_system, attribute, value)` — scalar or list attr setter
   - `emit_particles(particle_system, count, position, velocity)` — inject particles via `cmds.emit`
4. Created `actions/deformer_advanced.py` with 3 new actions:
   - `create_cluster(objects, name, relative)` — cluster deformer with optional relative mode
   - `set_cluster_weights(cluster_node, mesh, weights, vertex_indices, normalize)` — per-vertex weights via `cmds.percent`
   - `create_lattice(objects, divisions, name, local_scale)` — FFD lattice via `cmds.lattice`
5. Fixed `__init__.py`: added `create_follicle`/`get_closest_point_on_surface` to `_ACTIONS` registration (were in `__all__` but missing from `register_all`)
6. Updated `__init__.py` imports, `__all__` (172 entries), `_ACTIONS` (168 registered)
7. Created `tests/test_actions_round18.py` with 57 tests (all passing):
   - `TestExportAnimationCurves` (7), `TestImportAnimationCurves` (4), `TestQuerySceneTimeInfo` (3)
   - `TestCreateParticleSystem` (5), `TestGetParticleSystemInfo` (5), `TestSetParticleAttribute` (5), `TestEmitParticles` (5)
   - `TestCreateCluster` (6), `TestSetClusterWeights` (7), `TestCreateLattice` (8), `TestRegisterAllRound18` (3)

### State after this round
- Tests: **1081 passing** (all pass), 0 failures
- `__all__` actions: 172
- Committed: `19bbc6f feat(skills): add particles, cluster/lattice deformers, export/import animation curves, scene time query actions`
- Pushed: `origin/auto-improve` updated (b666f55..19bbc6f)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- `_ACTIONS` registration count (168) vs `__all__` count (172): some actions in `__all__` have no `register_all` entry; consider reconciling
- Next action candidates:
  - `set_render_quality(quality_preset)` — high/medium/low quick render preset
  - `create_nucleus(name, gravity, wind_speed)` — create nDynamics nucleus solver
  - `create_dynamic_field(field_type, magnitude)` — gravity/turbulence/radial field
  - `get_particle_count(particle_system)` — fast count query
  - `set_nucleus_attribute(nucleus, attribute, value)` — set nDynamics solver attrs
  - `wire_deformer(curve, objects)` — wire deformer along a curve
  - `sculpt_deformer(objects, mode)` — sculpt deformer (stretch/project/flip)
  - `proximity_wrap(driver, driven)` — proximity wrap deformer
  - `add_dynamic_attribute(object_name, attr_name)` — add per-particle runtime attr


### State before this round
- Branch: `auto-improve` at `dc3950f`, origin/main unchanged at `6b90561`
- Actions: 156 registered
- Tests: 971 passing, coverage 95%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Added 3 new animation actions to `animation.py`:
   - `list_animation_curves(object_name, attribute)` — list all animCurve nodes driving an object, with type/key_count/attribute info
   - `set_animation_curve_tangent(object_name, attribute, frame, tangent_type, in/out)` — set in/out tangent type on all or specific keys
   - `bake_constraints(objects, start_frame, end_frame, sample_by, remove_constraints)` — bake constraint-driven anim to keyframes; optionally delete constraints
3. Added 2 new actions to `motion_path.py`:
   - `create_follicle(mesh, u_pos, v_pos, name)` — create standalone follicle node on mesh or NURBS surface at UV coords
   - `get_closest_point_on_surface(surface, point)` — query closest position/normal/UV on NURBS (closestPointOnSurface) or mesh (closestPointOnMesh)
4. Added 1 new rigging action to `rigging.py`:
   - `set_ik_fk_blend(ik_handle, blend, attribute)` — set IK/FK blend weight (0=FK, 1=IK) on ikHandle node
5. Registered all 6 new actions in `actions/__init__.py` → total **162 actions**
6. Created `tests/test_actions_round17.py` with 53 tests (all passing):
   - `TestListAnimationCurves` (7), `TestSetAnimationCurveTangent` (10), `TestBakeConstraints` (8)
   - `TestCreateFollicle` (8), `TestGetClosestPointOnSurface` (8), `TestSetIkFkBlend` (10), `TestRegisterAllRound17` (2)

### State after this round
- Tests: **1024 passing** (all pass), 0 failures
- Coverage: 95%+ (new functions fully covered)
- Committed: `b666f55 feat(skills): add list_animation_curves, set_animation_curve_tangent, bake_constraints, create_follicle, get_closest_point_on_surface, set_ik_fk_blend actions`
- Pushed: `origin/auto-improve` updated (dc3950f..b666f55)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `get_particle_system_info(particle_system)` — query nParticle/particle node attributes
  - `set_render_quality(quality_preset)` — quick high/medium/low render quality preset
  - `export_animation_curves(object_name, file_path)` — export anim curves to file
  - `import_animation_curves(object_name, file_path)` — import/apply anim curves from file
  - `create_cluster(objects, name)` — create cluster deformer with weight set
  - `set_cluster_weight(cluster, weights)` — set per-vertex weights on a cluster
  - `create_lattice(objects, divisions)` — create FFD lattice deformer
  - `query_scene_time_info()` — query FPS, timeline ranges, current time as single call

---

## 2026-04-09 (Round 16 — blend shape queries, joint label, deformer utils, motion path, surface attachment)

### State before this round
- Branch: `auto-improve` at `b418f27`, origin/main unchanged at `6b90561`
- Actions: 149 registered
- Tests: 919 passing, coverage 96%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Created `actions/rigging_ext.py` with 3 new rigging extension actions:
   - `get_blend_shape_targets(blend_shape)` — query all target names/indices/weights from a blendShape node
   - `set_blend_shape_weight(blend_shape, target, weight)` — set target weight by alias name or index string
   - `set_joint_label(joint_name, side, label_type, other_label)` — label joint side/type for mirror naming
3. Created `actions/deformer_utils.py` with 2 deformer stack actions:
   - `list_deformers(object_name, deformer_type)` — list geometryFilter nodes in construction history
   - `reorder_deformers(object_name, deformer_order)` — reorder deformer stack using `cmds.reorderDeformers`
4. Created `actions/motion_path.py` with 2 motion/surface attachment actions:
   - `create_motion_path(object_name, curve, start_frame, end_frame, follow, ...)` — attach to NURBS curve via `cmds.pathAnimation`
   - `attach_to_surface(object_name, surface, param_u, param_v, constraint_type)` — geometryConstraint or follicle-based surface attachment
5. Registered all 7 new actions in `actions/__init__.py` → total **156 actions**
6. Created `tests/test_actions_round16.py` with 52 tests (all passing):
   - `TestGetBlendShapeTargets` (7), `TestSetBlendShapeWeight` (8), `TestSetJointLabel` (8)
   - `TestListDeformers` (5), `TestReorderDeformers` (5)
   - `TestCreateMotionPath` (9), `TestAttachToSurface` (8), `TestRegisterAllRound16` (2)

### State after this round
- Tests: **971 passing** (all pass), 0 failures
- Coverage: 95% total (new modules: rigging_ext 92%, deformer_utils 90%, motion_path 88%)
- Committed: `dc3950f feat(skills): add get_blend_shape_targets, set_blend_shape_weight, set_joint_label, list_deformers, reorder_deformers, create_motion_path, attach_to_surface actions`
- Pushed: `origin/auto-improve` updated (b418f27..dc3950f)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- `motion_path.py` follicle path lines — complex parent/connect chain; could add more tests
- Next action candidates:
  - `bake_constraints(objects, start_frame, end_frame)` — bake with constraint overrides
  - `set_ik_fk_blend(ik_handle, blend)` — IK/FK blend attribute
  - `create_follicle(mesh, u_pos, v_pos)` — standalone follicle creation (without attaching an object)
  - `get_closest_point_on_surface(surface, point)` — query closest UV/position on a surface
  - `create_particle_system(name, particle_count, position)` — Maya nParticle/particle setup
  - `set_render_quality(quality_preset)` — quick high/medium/low render quality preset
  - `list_animation_curves(object_name)` — list animCurve nodes on an object
  - `set_animation_curve_tangent(object_name, attribute, frame, tangent_type)` — adjust tangent type on existing keys


### State before this round
- Branch: `auto-improve` at `baf3b99`, origin/main unchanged at `6b90561`
- Actions: 138 registered
- Tests: 848 passing, coverage 96%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Created `actions/skin_weights.py` with 3 new actions:
   - `get_skin_weights(mesh, skin_cluster, vertex_indices)` — query per-vertex weight dict using `cmds.ls(history, type="skinCluster")` for reliable detection
   - `paint_skin_weights(mesh, joint, weight, vertex_indices, skin_cluster, normalize)` — set weights via `cmds.skinPercent`
   - `mirror_skin_weights(mesh, mirror_axis, skin_cluster, ...)` — mirror via `cmds.copySkinWeights`
3. Created `actions/mesh_normals.py` with 3 new actions:
   - `get_mesh_normals(object_name, vertex_indices, world_space)` — query via `polyNormalPerVertex`, averages face normals per vertex
   - `set_mesh_normal(object_name, vertex_index, normal)` — unlock + set custom vertex normal
   - `soften_normals(object_name, angle, harden)` — edge normal softening/hardening via `polySoftEdge`
4. Created `actions/transforms.py` with 3 new actions:
   - `get_object_matrix(object_name, world_space)` — query world/local matrix as 4×4 nested list + flat 16-element list
   - `set_object_matrix(object_name, matrix, world_space)` — apply matrix via `xform`, accepts 4×4 or flat input
   - `reset_transform(object_name, translate, rotate, scale)` — zero/identity reset without freezing
5. Added `create_constraint_weighted(sources, target, weights, constraint_type, ...)` to `constraints.py`
   - Multi-source weighted constraint; pads missing weights to 1.0
6. Added `create_polygon_text(text, name, font, depth, extrude)` to `scene_utils.py`
   - Uses `cmds.textCurves` + `cmds.extrude`; graceful fallback if extrude fails per curve
7. Registered all 11 new actions in `actions/__init__.py` → total **149 actions**
8. Created `tests/test_actions_round15.py` with 71 tests (all passing):
   - `TestGetSkinWeights` (7), `TestPaintSkinWeights` (8), `TestMirrorSkinWeights` (6)
   - `TestGetMeshNormals` (7), `TestSetMeshNormal` (5), `TestSoftenNormals` (5)
   - `TestGetObjectMatrix` (4), `TestSetObjectMatrix` (6), `TestResetTransform` (5)
   - `TestCreateConstraintWeighted` (9), `TestCreatePolygonText` (7), `TestRegisterAllRound15` (2)

### State after this round
- Tests: **919 passing** (all pass), 0 failures
- Coverage: 96%+ (new modules fully covered)
- Committed: `b418f27 feat(skills): add skin_weights, mesh_normals, transforms (matrix), create_constraint_weighted, create_polygon_text actions`
- Pushed: `origin/auto-improve` updated (baf3b99..b418f27)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `set_joint_label(joint_name, side, label_type)` — joint side/label for mirror naming
  - `get_blend_shape_targets(blend_shape)` — list target names and current weights
  - `set_blend_shape_weight(blend_shape, target, weight)` — drive blend shape weight
  - `constrain_to_surface(source, target_surface)` — geometry constraint (rivet)
  - `create_follicle(mesh, u_pos, v_pos)` — attach follicle to mesh surface
  - `bake_constraints(objects, start_frame, end_frame)` — bake with constraint override
  - `create_motion_path(object_name, curve, follow)` — attach object to motion path
  - `set_ik_fk_blend(ik_handle, blend)` — IK/FK blend attribute
  - `list_deformers(object_name)` — list all deformers on a mesh
  - `reorder_deformers(object_name, deformer_order)` — change deformation order


### State before this round
- Branch: `auto-improve` at `c49d9fb`, origin/main unchanged at `6b90561`
- Actions: 119 registered
- Tests: 728 passing, coverage 96%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Created `actions/uv_ops.py` with 5 UV operation actions:
   - `get_uv_info(object_name, uv_set)` — query UV sets and optionally UV coordinates
   - `create_uv_set(object_name, uv_set_name, copy_from)` — create new UV set with optional copy
   - `delete_uv_set(object_name, uv_set_name)` — delete UV set (protects the only remaining set)
   - `project_uvs(object_name, projection_type, axis)` — planar/cylindrical/spherical UV projection
   - `copy_uvs(source, target, source_uv_set, target_uv_set)` — copy UV layout via transferAttributes
3. Created `actions/vertex_color.py` with 4 vertex color actions:
   - `set_vertex_color(object_name, color, alpha, vertices, color_set)` — set vertex RGBA per object or vertex list
   - `get_vertex_color(object_name, vertex_index, color_set)` — query color sets or per-vertex RGBA
   - `create_color_set(object_name, color_set_name, representation)` — create RGB/RGBA color set
   - `remove_vertex_colors(object_name, color_set)` — delete specific or all color sets
4. Created `actions/texture_bake.py` with 3 texture/color management actions:
   - `bake_textures(objects, file_path, resolution, bake_type, renderer, overscan)` — bake via convertSolidTx
   - `set_color_management(enabled, input_color_space, rendering_space, output_transform)` — configure OCIO/Maya color management
   - `list_color_spaces()` — list all registered input/rendering/output color spaces
5. Registered all 12 new actions in `actions/__init__.py` → total **131 actions**
6. Created `tests/test_actions_round13.py` with 64 tests (all passing):
   - `TestGetUvInfo` (6), `TestCreateUvSet` (5), `TestDeleteUvSet` (4), `TestProjectUvs` (6), `TestCopyUvs` (4)
   - `TestSetVertexColor` (5), `TestGetVertexColor` (5), `TestCreateColorSet` (5), `TestRemoveVertexColors` (4)
   - `TestBakeTextures` (8), `TestSetColorManagement` (7), `TestListColorSpaces` (3), `TestRegisterAllRound13` (2)

### State after this round
- Tests: **792 passing** (all pass), 0 failures
- Coverage: 96%+ (new modules fully covered)
- Committed: `a877dd3 feat(skills): add uv_ops, vertex_color, texture_bake actions`
- Pushed: `origin/auto-improve` updated (c49d9fb..a877dd3)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `get_uv_shell_info(object_name)` — list UV shells with bounding boxes
  - `unfold_uvs(object_name, iterations)` — unfold UV layout
  - `normalize_uvs(object_name, layout_u, layout_v)` — normalize UVs to 0-1 space
  - `blend_shape_add_target(blend_shape, target_mesh)` — add target to existing blend shape
  - `set_driven_key(driver_attr, driven_attrs, driver_values, driven_values)` — driven key setup
  - `create_constraint_weighted(sources, target, weights, constraint_type)` — weighted constraint
  - `toggle_gpu_override(object_name, enabled)` — Maya GPU override display mode
  - `set_object_color(object_name, color_index)` — set viewport wire color



---

## 2026-04-09 (Round 14 — UV shells, unfold/normalize, blend-shape target, SDK, object colour, GPU override)

### State before this round
- Branch: `auto-improve` at `a877dd3`, origin/main unchanged at `6b90561`
- Actions: 131 registered
- Tests: 792 passing, coverage 96%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Extended `uv_ops.py` with 3 new UV actions:
   - `get_uv_shell_info(object_name, uv_set)` — query UV shell count and per-shell bounding boxes via `polyEvaluate(uvShellsIds=True)`
   - `unfold_uvs(object_name, iterations, optimize_scale)` — unfold UV layout via `u3dUnfold`, optional `u3dOptimize`
   - `normalize_uvs(object_name, layout_u, layout_v, preserve_aspect)` — normalize UV coords via `polyNormalizeUV`
3. Extended `rigging.py` with 2 new actions:
   - `blend_shape_add_target(blend_shape, target_mesh, weight, index)` — add target mesh to existing blendShape via `cmds.blendShape(edit=True, target=...)`
   - `set_driven_key(driver_attr, driven_attrs, driver_values, driven_values, tangent_type)` — create SDK curves via `cmds.setDrivenKeyframe`
4. Extended `scene_utils.py` with 2 new display/GPU actions:
   - `set_object_color(object_name, color_index, use_default)` — set wireframe override colour (0–31) via `overrideEnabled`/`overrideColor`
   - `toggle_gpu_override(object_name, enabled)` — toggle bounding-box display type via `overrideDisplayType`
5. Registered all 7 new actions in `actions/__init__.py` → total **138 actions**
6. Created `tests/test_actions_round14.py` with 56 tests (all passing):
   - `TestGetUvShellInfo` (6), `TestUnfoldUVs` (8), `TestNormalizeUVs` (7)
   - `TestBlendShapeAddTarget` (8), `TestSetDrivenKey` (10)
   - `TestSetObjectColor` (9), `TestToggleGpuOverride` (6), `TestRegisterAllRound14` (2)
7. Cleaned up stale `.txt` test output files; added `*.txt` to `.gitignore`

### State after this round
- Tests: **848 passing** (all pass), 0 failures
- Coverage: 96%+ (new modules/functions fully covered)
- Committed: `0ab2f26 feat(skills): add get_uv_shell_info, unfold_uvs, normalize_uvs, blend_shape_add_target, set_driven_key, set_object_color, toggle_gpu_override actions`
- Pushed: `origin/auto-improve` updated (a877dd3..baf3b99)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `create_constraint_weighted(sources, target, weights, constraint_type)` — weighted multi-source constraint
  - `set_joint_label(joint_name, side, label_type)` — joint labeling for mirror naming
  - `get_object_matrix(object_name)` — world matrix as 4x4 list
  - `set_object_matrix(object_name, matrix)` — set object world transform from matrix
  - `list_uv_shells(object_name)` — alias providing UV shell membership per face
  - `create_polygon_text(text, font, depth)` — create 3D polygon text
  - `paint_skin_weights(joint_name, mesh, values)` — programmatic skin weight painting
  - `mirror_skin_weights(mesh, mirror_axis)` — mirror skin weights across axis
  - `get_mesh_normals(object_name)` — query vertex normals
  - `set_mesh_normal(object_name, vertex_index, normal)` — set custom vertex normal



---

## 2026-04-09 (Round 22 — nRigid control, mesh combine/separate/extract/mirror)

### State before this round
- Branch: `auto-improve` at `bc6ce4f`, origin/main unchanged at `6b90561`
- Actions: 189 (`__all__`)
- Tests: 1219 passing, coverage 95%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Extended `dynamics.py` with 2 new nRigid control actions:
   - `set_nrigid_attribute(nrigid_node, attribute, value)` — set scalar/triple/string on nRigid shape node; validates type is `nRigid`
   - `list_nrigid_nodes()` — enumerate all nRigid shapes with parent transform and connected nucleus info
3. Extended `mesh_ops.py` with 4 new mesh topology actions:
   - `combine_meshes(objects, name)` — combine multiple polygon meshes via `cmds.polyUnite`
   - `separate_mesh(object_name)` — separate disconnected shells via `cmds.polySeparate`
   - `extract_faces(object_name, face_indices, keep_original, separate)` — extract faces via `cmds.polyChipOff` + optional `polySeparate`
   - `mirror_mesh(object_name, axis, cut_position, merge_threshold, merge_border)` — mirror mesh via `cmds.polyMirrorFace`
4. Updated `actions/__init__.py` → total **195 in `__all__`**, registered in `_ACTIONS`
5. Created `tests/test_actions_round22.py` with 47 tests (all passing):
   - `TestSetNrigidAttribute` (9), `TestListNrigidNodes` (6)
   - `TestCombineMeshes` (7), `TestSeparateMesh` (6), `TestExtractFaces` (7), `TestMirrorMesh` (10)
   - `TestRegisterAllRound22` (2)
6. Fixed test fixture pattern: must set `mock_maya_mod.cmds = mock_cmds` and register both `sys.modules["maya"]` and `sys.modules["maya.cmds"]` to avoid mock bypass via `MagicMock().cmds` attribute auto-creation

### State after this round
- Tests: **1266 passing** (all pass), 0 failures
- `__all__` actions: 195
- Committed: `0dfcae8 feat(skills): add set_nrigid_attribute, list_nrigid_nodes, combine_meshes, separate_mesh, extract_faces, mirror_mesh actions`
- Pushed: `origin/auto-improve` updated (bc6ce4f..0dfcae8)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `weld_border_edges(object_name, threshold)` — merge open border edges via `polyMerge`
  - `get_mesh_vertex_info(object_name, vertex_indices)` — query vertex world position/normal
  - `flip_normals(object_name)` — reverse polygon normals
  - `bridge_edges(object_name, edge_loop_a, edge_loop_b)` — bridge two edge loops
  - `get_render_pass_list()` — list AOV/render passes defined in scene
  - `create_render_pass(name, pass_type)` — create a render pass for AOV
  - `set_time_warp(frame_values, time_values)` — create a time warp on the time slider
  - `query_skincluster_info(mesh)` — get skin cluster info (joints, max influences) from a mesh


### State before this round
- Branch: `auto-improve` at `44a6297`, origin/main unchanged at `6b90561`
- Actions: 183 (`__all__`)
- Tests: 1171 passing, coverage 95%

### Work done
1. Verified `origin/main` has no new commits; no rebase needed
2. Extended `dynamics.py` with 2 new nCloth control actions:
   - `set_ncloth_attribute(ncloth_node, attribute, value)` — set scalar/vector/string on nCloth shape node; validates type is `nCloth`
   - `list_ncloth_nodes()` — enumerate all nCloth shapes with parent transform and connected nucleus info
3. Extended `mesh_ops.py` with 3 new actions:
   - `get_mesh_edge_info(object_name, edge_indices)` — query edge length (via `pointPosition`) and connected vertices (via `polyInfo`); supports specific index list or all edges
   - `select_by_material(material_name)` — find shading groups, resolve members to transforms, deduplicate, call `cmds.select`
   - `create_proxy_mesh(object_name, reduction, name)` — duplicate + `polyReduce(percentage=(1-reduction)*100)`; validates reduction in `[0, 1)`
4. Extended `scene_utils.py` with 1 new viewport action:
   - `set_shading_mode(mode, panel)` — set `wireframe/smooth/textured/flat/bounding_box` via `cmds.modelEditor`
5. Updated `actions/__init__.py`: merged imports, removed duplicate blocks, added 6 new entries → **189 in `__all__`**
6. Created `tests/test_actions_round21.py` with 48 tests (all passing)

### State after this round
- Tests: **1219 passing** (all pass), 0 failures
- `__all__` actions: 189
- Committed: `bc6ce4f feat(skills): add set_ncloth_attribute, list_ncloth_nodes, get_mesh_edge_info, select_by_material, create_proxy_mesh, set_shading_mode actions`
- Pushed: `origin/auto-improve` updated (44a6297..bc6ce4f)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Next action candidates:
  - `set_nrigid_attribute(nrigid_node, attribute, value)` — set passive collider properties
  - `list_nrigid_nodes()` — enumerate nRigid collider nodes
  - `get_mesh_vertex_info(object_name, vertex_indices)` — query vertex world position/normal
  - `combine_meshes(objects, name)` — combine multiple meshes into one
  - `separate_mesh(object_name)` — separate disconnected mesh shells
  - `extract_faces(object_name, face_indices)` — extract/separate polygon face regions
  - `mirror_mesh(object_name, axis, cut_position)` — mirror mesh along world axis
  - `weld_border_edges(object_name, threshold)` — merge open border edges
  - `get_render_pass_list()` — list AOV/render passes defined in scene
  - `create_render_pass(name, pass_type)` — create a render pass for AOV








