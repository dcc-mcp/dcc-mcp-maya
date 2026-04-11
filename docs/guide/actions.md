# Available Actions

`dcc-mcp-maya` ships **200+ built-in actions** organized into 39 skill packages. Each action becomes an MCP tool that AI agents can call directly.

## Naming Convention

Actions follow the pattern: `{skill_name_underscored}__{script_stem}`

Examples:
- `maya_scene__new_scene`
- `maya_primitives__create_sphere`
- `maya_animation__set_keyframe`

## Skill Packages

### maya-scene (21 actions)

Scene lifecycle, object management, hierarchy, and basic queries.

| Action | Description |
|--------|-------------|
| `maya_scene__new_scene` | Create a new empty Maya scene |
| `maya_scene__open_scene` | Open a Maya scene file |
| `maya_scene__save_scene` | Save the current scene |
| `maya_scene__export_scene` | Export the scene to FBX/OBJ/Alembic/Maya |
| `maya_scene__list_objects` | List DAG objects (optional type filter) |
| `maya_scene__get_selection` | Get the current selection |
| `maya_scene__set_selection` | Set the active selection |
| `maya_scene__select_by_type` | Select all objects of a given Maya node type |
| `maya_scene__get_session_info` | Maya version, scene path, FPS, object count |
| `maya_scene__get_scene_info` | Hierarchical DAG description of the scene |
| `maya_scene__group_objects` | Group objects under a new group node |
| `maya_scene__parent_object` | Set or clear the parent of an object |
| `maya_scene__duplicate_object` | Duplicate an object |
| `maya_scene__freeze_transforms` | Freeze transforms on an object |
| `maya_scene__center_pivot` | Center pivot to bounding box |
| `maya_scene__get_bounding_box` | Query world-space bounding box |
| `maya_scene__set_visibility` | Show or hide an object |
| `maya_scene__lock_object` | Lock/unlock transform attributes |
| `maya_scene__set_frame_rate` | Change scene playback frame rate |
| `maya_scene__list_cameras` | List all cameras in the scene |
| `maya_scene__create_locator` | Create a Maya locator node |

**`maya_scene__new_scene` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `bool` | `false` | Discard unsaved changes without prompting |

**`maya_scene__list_objects` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `object_type` | `str` | `null` | Maya type filter (e.g. `"mesh"`, `"transform"`, `"joint"`) |
| `dag` | `bool` | `true` | Return only DAG nodes |

Returns `context.objects` (list) and `context.count`.

**`maya_scene__get_session_info` returns:**
`maya_version`, `api_version`, `python_version`, `scene_file`, `scene_modified`, `fps`, `up_axis`, `object_count`.

### maya-primitives (8 actions)

Polygon primitive creation and transform management.

| Action | Description |
|--------|-------------|
| `maya_primitives__create_sphere` | Create a polygon sphere |
| `maya_primitives__create_cube` | Create a polygon cube |
| `maya_primitives__create_cylinder` | Create a polygon cylinder |
| `maya_primitives__create_plane` | Create a polygon plane |
| `maya_primitives__delete_objects` | Delete objects from the scene |
| `maya_primitives__set_transform` | Set translate/rotate/scale |
| `maya_primitives__get_transform` | Get translate/rotate/scale |
| `maya_primitives__rename_object` | Rename an object |

**`maya_primitives__create_sphere` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `radius` | `float` | `1.0` | Sphere radius in scene units |
| `name` | `str` | `null` | Optional name for the created object |

Returns `context.object_name`.

**`maya_primitives__set_transform` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `object_name` | `str` | required | Object to transform |
| `translate` | `[float, float, float]` | `null` | `[tx, ty, tz]` in scene units. `null` = no change |
| `rotate` | `[float, float, float]` | `null` | `[rx, ry, rz]` in degrees. `null` = no change |
| `scale` | `[float, float, float]` | `null` | `[sx, sy, sz]`. `null` = no change |

### maya-animation (13 actions)

Keyframes, timeline, curves, simulation baking, and animation I/O.

| Action | Description |
|--------|-------------|
| `maya_animation__set_keyframe` | Set a keyframe on an attribute at a given time |
| `maya_animation__get_keyframes` | Get all keyframe times for an object/attribute |
| `maya_animation__delete_keyframes` | Delete keyframes within an optional frame range |
| `maya_animation__set_timeline` | Set playback and animation timeline range |
| `maya_animation__get_current_time` | Get current frame number |
| `maya_animation__set_current_time` | Set current frame number |
| `maya_animation__query_scene_time_info` | Query scene time and playback settings |
| `maya_animation__bake_simulation` | Bake simulation/constraints to keyframes |
| `maya_animation__bake_constraints` | Bake constraint-driven animation to keyframes |
| `maya_animation__list_animation_curves` | List animCurve nodes driving an object |
| `maya_animation__set_animation_curve_tangent` | Set tangent type on keyframes |
| `maya_animation__export_animation_curves` | Export animation curves to `.anim` file |
| `maya_animation__import_animation_curves` | Import animation curves from a file |

**`maya_animation__set_keyframe` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `object_name` | `str` | required | Name of the object to keyframe |
| `attribute` | `str` | `null` | Single attribute name (e.g. `"translateX"`). Takes priority over `attributes` |
| `attributes` | `list[str]` | `null` | List of attributes to key. Ignored when `attribute` is set |
| `time` | `float` | current | Frame number. Defaults to current time |
| `value` | `float` | `null` | Explicit value to set before keying (single attribute only) |

Returns `context.keyframe_count`.

**`maya_animation__get_keyframes` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `object_name` | `str` | required | Object to query |
| `attribute` | `str` | `null` | Specific attribute (e.g. `"tx"`). `null` = all attributes |

Returns `context.keyframes` (list of frame numbers) and `context.count`.

**`maya_animation__bake_simulation` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `objects` | `list[str]` | `null` | Objects to bake. `null` = use current selection |
| `start_frame` | `float` | `1.0` | First frame of bake range |
| `end_frame` | `float` | `120.0` | Last frame of bake range |
| `sample_by` | `float` | `1.0` | Baking interval (e.g. `0.5` = every half-frame) |

Returns `context.object_count`, `context.objects`, `context.start_frame`, `context.end_frame`.

### maya-materials (8 actions)

Shader creation, assignment, and attribute editing.

| Action | Description |
|--------|-------------|
| `maya_materials__create_material` | Create Lambert/Blinn/Phong/aiStandardSurface |
| `maya_materials__assign_material` | Assign material to objects |
| `maya_materials__set_material_attribute` | Set color, roughness, metalness, etc. |
| `maya_materials__list_materials` | List all scene materials |
| `maya_materials__list_shading_groups` | List all shading groups |
| `maya_materials__get_material_connections` | Get texture/node connections on a material |
| `maya_materials__get_shader_assignment` | Get material assigned to an object |
| `maya_materials__reset_to_default_material` | Reset object to default Lambert material |

**`maya_materials__create_material` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `material_type` | `str` | `"lambert"` | Shader node type: `lambert`, `blinn`, `phong`, `phongE`, `aiStandardSurface` |
| `shader_type` | `str` | `null` | Legacy alias for `material_type` |
| `name` | `str` | `null` | Optional name for the created material |

Returns `context.material_name` and `context.shading_group`.

**`maya_materials__set_material_attribute` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `material_name` | `str` | required | Name of the material node |
| `attribute` | `str` | required | Attribute name (e.g. `"color"`, `"transparency"`, `"metalness"`) |
| `value` | `any` | required | Scalar, `[r, g, b]` (RGB), or `[r, g, b, a]` (RGBA) |

### maya-rigging (12 actions)

Joints, IK, blend shapes, skin binding, and constraints.

| Action | Description |
|--------|-------------|
| `maya_rigging__create_joint` | Create a joint |
| `maya_rigging__skin_cluster_bind` | Smooth bind mesh to skeleton |
| `maya_rigging__create_blend_shape` | Create a blend shape deformer |
| `maya_rigging__blend_shape_add_target` | Add a target to an existing blend shape |
| `maya_rigging__assign_deformer` | Assign a deformer to a mesh |
| `maya_rigging__create_ik_handle` | Create an IK handle |
| `maya_rigging__set_ik_fk_blend` | Set IK/FK blend attribute |
| `maya_rigging__mirror_joints` | Mirror joints across an axis |
| `maya_rigging__set_joint_orient` | Set joint orientation |
| `maya_rigging__set_joint_limit` | Set joint rotation limits |
| `maya_rigging__set_driven_key` | Create a Set Driven Key connection |
| `maya_rigging__create_curve` | Create a NURBS curve |

**`maya_rigging__skin_cluster_bind` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `joints` | `list[str]` | required | List of joint names to include in the skin cluster |
| `mesh` | `str` | required | Name of the mesh to skin |
| `max_influences` | `int` | `4` | Maximum joint influences per vertex |
| `bind_method` | `int` | `0` | Binding algorithm: `0`=closest distance, `1`=closest joint, `2`=heat map, `3`=geodesic voxel |
| `name` | `str` | `null` | Optional name for the skin cluster node |

Returns `context.skin_cluster_name` and `context.joint_count`.

**`maya_rigging__create_joint` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `null` | Name for the new joint. Maya auto-names if `null` |
| `position` | `[float, float, float]` | `[0, 0, 0]` | World-space `[x, y, z]` position |
| `parent` | `str` | `null` | Existing transform/joint to parent under. `null` = world root |

Returns `context.object_name`, `context.position`, `context.parent`.

### maya-mesh-ops (12 actions)

Mesh editing, boolean operations, and geometry utilities.

| Action | Description |
|--------|-------------|
| `maya_mesh_ops__combine_meshes` | Combine multiple meshes |
| `maya_mesh_ops__separate_mesh` | Separate a mesh into shells |
| `maya_mesh_ops__extract_faces` | Extract selected faces to a new mesh |
| `maya_mesh_ops__mirror_mesh` | Mirror a mesh across an axis |
| `maya_mesh_ops__triangulate` | Triangulate a polygon mesh |
| `maya_mesh_ops__apply_subdivision` | Apply subdivision to a mesh |
| `maya_mesh_ops__cleanup_mesh` | Clean up mesh geometry (remove invalid faces, etc.) |
| `maya_mesh_ops__merge_vertices` | Merge vertices within a threshold |
| `maya_mesh_ops__get_poly_count` | Get polygon/vertex/edge count |
| `maya_mesh_ops__get_mesh_edge_info` | Get edge connectivity and lengths |
| `maya_mesh_ops__select_by_material` | Select faces assigned to a material |
| `maya_mesh_ops__create_proxy_mesh` | Create a low-poly proxy |

**`maya_mesh_ops__cleanup_mesh` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `object_name` | `str` | required | Transform or mesh name |
| `non_manifold` | `bool` | `true` | Fix non-manifold geometry |
| `lamina_faces` | `bool` | `true` | Remove lamina (zero-area) faces |
| `invalid_components` | `bool` | `true` | Remove invalid (degenerate) polygons |

### maya-uv-ops (8 actions)

UV editing and layout operations.

| Action | Description |
|--------|-------------|
| `maya_uv_ops__project_uvs` | Apply UV projection (planar/cylindrical/spherical) |
| `maya_uv_ops__unfold_uvs` | Unfold UVs |
| `maya_uv_ops__normalize_uvs` | Normalize UVs into 0-1 space |
| `maya_uv_ops__copy_uvs` | Copy UVs between meshes |
| `maya_uv_ops__create_uv_set` | Create a new UV set |
| `maya_uv_ops__delete_uv_set` | Delete a UV set |
| `maya_uv_ops__get_uv_info` | Get UV coordinates and shell count |
| `maya_uv_ops__get_uv_shell_info` | Get UV shell information |

### maya-render (8 actions)

Render settings, viewport capture, and file I/O.

| Action | Description |
|--------|-------------|
| `maya_render__set_render_settings` | Set resolution, frame range, renderer |
| `maya_render__get_render_settings` | Query current render settings |
| `maya_render__capture_viewport` | Capture viewport as base64 PNG |
| `maya_render__import_file` | Import FBX/OBJ/Alembic/Maya file |
| `maya_render__export_selection` | Export selection to FBX/OBJ/Alembic |
| `maya_render__set_render_quality` | Set render quality presets |
| `maya_render__get_scene_render_stats` | Get renderer and resolution info |
| `maya_render__playblast` | Record viewport playblast |

**`maya_render__capture_viewport` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `width` | `int` | `1920` | Image width in pixels |
| `height` | `int` | `1080` | Image height in pixels |
| `frame` | `float` | current | Frame to capture. Defaults to current frame |

Returns `context.image` (base64-encoded PNG string), `context.width`, `context.height`, `context.frame`.

### maya-node-graph (9 actions)

Node connections, history, and mesh operations via the DG.

| Action | Description |
|--------|-------------|
| `maya_node_graph__connect_attr` | Connect two node attributes |
| `maya_node_graph__disconnect_attr` | Disconnect a node attribute |
| `maya_node_graph__list_connections` | List connections on a node |
| `maya_node_graph__get_dag_path` | Get full DAG path for an object |
| `maya_node_graph__list_history` | List construction history nodes |
| `maya_node_graph__delete_history` | Delete construction history |
| `maya_node_graph__smooth_mesh` | Subdivide/smooth a mesh |
| `maya_node_graph__transfer_attributes` | Transfer UVs and attributes between meshes |
| `maya_node_graph__apply_symmetry` | Apply symmetry to a mesh |

### maya-cameras (5 actions)

Camera creation, framing, and settings.

| Action | Description |
|--------|-------------|
| `maya_cameras__create_camera` | Create a camera |
| `maya_cameras__set_camera_attribute` | Set focal length, aperture, etc. |
| `maya_cameras__get_camera_info` | Get camera properties |
| `maya_cameras__list_all_cameras` | List all cameras in the scene |
| `maya_cameras__set_active_camera` | Set the active viewport camera |

### maya-lighting (4 actions)

Light creation and attribute control.

| Action | Description |
|--------|-------------|
| `maya_lighting__create_light` | Create directional/point/spot/area light |
| `maya_lighting__set_light_attribute` | Set intensity, color, decay |
| `maya_lighting__list_lights` | List all lights in the scene |
| `maya_lighting__delete_light` | Delete a light |

### maya-deformers (5 actions)

Standard Maya deformers.

| Action | Description |
|--------|-------------|
| `maya_deformers__create_cluster` | Create cluster deformer |
| `maya_deformers__create_lattice` | Create lattice deformer |
| `maya_deformers__wire_deformer` | Create wire deformer |
| `maya_deformers__sculpt_deformer` | Create sculpt deformer |
| `maya_deformers__set_cluster_weights` | Set cluster deformer weights |

### maya-constraints (4 actions)

Standard Maya constraint nodes.

| Action | Description |
|--------|-------------|
| `maya_constraints__add_constraint` | Create parent/point/orient/scale constraint |
| `maya_constraints__create_constraint_weighted` | Create weighted constraint |
| `maya_constraints__list_constraints` | List constraints on an object |
| `maya_constraints__remove_constraint` | Remove a constraint |

### maya-dynamics (10 actions)

nCloth, nRigid, nucleus, and dynamic fields.

| Action | Description |
|--------|-------------|
| `maya_dynamics__create_ncloth` | Create nCloth simulation |
| `maya_dynamics__create_nrigid` | Create nRigid passive collider |
| `maya_dynamics__set_ncloth_attribute` | Set nCloth solver attributes |
| `maya_dynamics__set_nrigid_attribute` | Set nRigid attributes |
| `maya_dynamics__list_ncloth_nodes` | List nCloth nodes in scene |
| `maya_dynamics__list_nrigid_nodes` | List nRigid nodes in scene |
| `maya_dynamics__create_nucleus` | Create nucleus solver node |
| `maya_dynamics__set_nucleus_attribute` | Set nucleus gravity, wind, etc. |
| `maya_dynamics__create_dynamic_field` | Create gravity/turbulence/vortex field |
| `maya_dynamics__connect_field_to_objects` | Connect field to dynamic objects |

### maya-attributes (5 actions)

Custom attribute management.

| Action | Description |
|--------|-------------|
| `maya_attributes__add_attribute` | Add a custom attribute |
| `maya_attributes__set_attribute` | Set attribute value |
| `maya_attributes__get_attribute` | Get attribute value |
| `maya_attributes__list_attributes` | List attributes on a node |
| `maya_attributes__delete_attribute` | Delete a custom attribute |

### maya-references (6 actions)

Maya reference file management.

| Action | Description |
|--------|-------------|
| `maya_references__create_reference` | Reference an external Maya file |
| `maya_references__list_references` | List all references |
| `maya_references__remove_reference` | Remove a reference |
| `maya_references__reload_reference` | Reload a reference from disk |
| `maya_references__unload_reference` | Unload a reference (keep in scene) |
| `maya_references__list_namespaces` | List all namespaces from references |

### maya-scene-utils (7 actions)

Scene-level utilities, annotations, and object color.

| Action | Description |
|--------|-------------|
| `maya_scene_utils__align_objects` | Align objects to another object or axis |
| `maya_scene_utils__create_annotation` | Create an annotation note in the viewport |
| `maya_scene_utils__create_polygon_text` | Create 3D polygon text |
| `maya_scene_utils__set_object_color` | Set wireframe/shading color on an object |
| `maya_scene_utils__set_pivot` | Set the pivot point position |
| `maya_scene_utils__set_shading_mode` | Set wireframe/smooth/flat shading |
| `maya_scene_utils__toggle_gpu_override` | Toggle GPU cache override |

### maya-selection (5 actions)

Selection management and filters.

| Action | Description |
|--------|-------------|
| `maya_selection__convert_selection` | Convert between vertex/edge/face/object modes |
| `maya_selection__grow_selection` | Grow selection by one step |
| `maya_selection__shrink_selection` | Shrink selection by one step |
| `maya_selection__invert_selection` | Invert the current selection |
| `maya_selection__select_similar` | Select objects similar to selection |

### maya-sets (4 actions)

Maya object sets.

| Action | Description |
|--------|-------------|
| `maya_sets__create_set` | Create an object set |
| `maya_sets__add_to_set` | Add objects to a set |
| `maya_sets__remove_from_set` | Remove objects from a set |
| `maya_sets__list_sets` | List all sets |

### maya-display (4 actions)

Display layers.

| Action | Description |
|--------|-------------|
| `maya_display__create_display_layer` | Create a display layer |
| `maya_display__set_display_layer` | Set display layer visibility/mode |
| `maya_display__list_display_layers` | List all display layers |
| `maya_display__delete_display_layer` | Delete a display layer |

### maya-render-layers (5 actions)

Render layer management.

| Action | Description |
|--------|-------------|
| `maya_render_layers__create_render_layer` | Create a render layer |
| `maya_render_layers__set_render_layer` | Switch to a render layer |
| `maya_render_layers__set_render_layer_attribute` | Set override attribute on a layer |
| `maya_render_layers__list_render_layers` | List all render layers |
| `maya_render_layers__delete_render_layer` | Delete a render layer |

### maya-mash (5 actions)

MASH procedural effects network.

| Action | Description |
|--------|-------------|
| `maya_mash__create_network` | Create a MASH network |
| `maya_mash__add_node` | Add a MASH node to a network |
| `maya_mash__set_mash_attribute` | Set MASH node attributes |
| `maya_mash__list_networks` | List all MASH networks |
| `maya_mash__delete_network` | Delete a MASH network |

### maya-bifrost (5 actions)

Bifrost graph and simulation.

| Action | Description |
|--------|-------------|
| `maya_bifrost__create_bifrost_graph` | Create a Bifrost graph |
| `maya_bifrost__add_bifrost_node` | Add a node to a Bifrost graph |
| `maya_bifrost__set_bifrost_property` | Set Bifrost node property |
| `maya_bifrost__list_bifrost_graphs` | List Bifrost graphs in scene |
| `maya_bifrost__connect_bifrost_ports` | Connect Bifrost node ports |

### maya-xgen (5 actions)

XGen groom and description management.

| Action | Description |
|--------|-------------|
| `maya_xgen__create_description` | Create an XGen description |
| `maya_xgen__delete_description` | Delete an XGen description |
| `maya_xgen__get_xgen_attribute` | Get XGen primitive attributes |
| `maya_xgen__set_xgen_attribute` | Set XGen primitive attributes |
| `maya_xgen__list_descriptions` | List XGen descriptions |

### maya-arnold-aov (5 actions)

Arnold AOV (Arbitrary Output Variable) management.

| Action | Description |
|--------|-------------|
| `maya_arnold_aov__add_aov` | Add an Arnold AOV |
| `maya_arnold_aov__list_aovs` | List all AOVs |
| `maya_arnold_aov__set_aov_attribute` | Set AOV attribute |
| `maya_arnold_aov__enable_aov` | Enable/disable an AOV |
| `maya_arnold_aov__delete_aov` | Delete an AOV |

### maya-namespaces (3 actions)

Namespace operations.

| Action | Description |
|--------|-------------|
| `maya_namespaces__set_namespace` | Move an object into a namespace |
| `maya_namespaces__rename_namespace` | Rename an existing namespace |
| `maya_namespaces__delete_namespace` | Delete a namespace |

### maya-scripting (2 actions)

MEL and Python execution inside Maya.

| Action | Description |
|--------|-------------|
| `maya_scripting__execute_mel` | Execute a MEL script inside Maya |
| `maya_scripting__execute_python` | Execute Python code inside Maya's interpreter |

**`maya_scripting__execute_mel` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `script` | `str` | required | MEL code string to execute |

Returns `context.output` (script result as string).

**`maya_scripting__execute_python` parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `code` | `str` | required | Python code string to execute in Maya's interpreter |

Returns `context.output`.

### maya-expressions (3 actions)

Maya expression nodes.

| Action | Description |
|--------|-------------|
| `maya_expressions__create_expression` | Create a Maya expression node |
| `maya_expressions__list_expressions` | List expression nodes in the scene |
| `maya_expressions__delete_expression` | Delete an expression node |

### maya-vertex-color (4 actions)

Vertex color operations.

| Action | Description |
|--------|-------------|
| `maya_vertex_color__set_vertex_color` | Set vertex colors on a mesh |
| `maya_vertex_color__get_vertex_color` | Get vertex colors |
| `maya_vertex_color__create_color_set` | Create a vertex color set |
| `maya_vertex_color__remove_vertex_colors` | Remove vertex colors from a mesh |

### maya-texture-bake (3 actions)

Texture baking and color management.

| Action | Description |
|--------|-------------|
| `maya_texture_bake__bake_textures` | Bake scene lighting to textures |
| `maya_texture_bake__list_color_spaces` | List available OCIO color spaces |
| `maya_texture_bake__set_color_management` | Configure OCIO color management settings |

### maya-utility (2 actions)

Utility nodes and scene statistics.

| Action | Description |
|--------|-------------|
| `maya_utility__create_utility_node` | Create any Maya utility or shading node by type |
| `maya_utility__get_scene_statistics` | Query polygon counts, node counts, and memory usage |

### maya-audio (5 actions)

Audio node management and timeline synchronization.

| Action | Description |
|--------|-------------|
| `maya_audio__import_audio` | Import an audio file into the scene |
| `maya_audio__list_audio_nodes` | List all audio nodes in the scene |
| `maya_audio__set_active_audio` | Set the active audio node for playback |
| `maya_audio__set_audio_offset` | Set the playback offset of an audio node |
| `maya_audio__delete_audio_node` | Delete an audio node |

### maya-cache (5 actions)

nCache and Alembic cache management.

| Action | Description |
|--------|-------------|
| `maya_cache__create_ncache` | Create an nCache for dynamic objects |
| `maya_cache__delete_cache` | Delete an existing cache |
| `maya_cache__list_caches` | List all caches in the scene |
| `maya_cache__export_alembic` | Export objects to Alembic (.abc) cache |
| `maya_cache__import_alembic` | Import an Alembic cache file |

### maya-fluid (5 actions)

Maya Fluid Effects (legacy fluid simulation).

| Action | Description |
|--------|-------------|
| `maya_fluid__create_fluid_container` | Create a fluid container |
| `maya_fluid__add_fluid_emitter` | Add a fluid emitter to a container |
| `maya_fluid__set_fluid_attribute` | Set fluid container simulation attributes |
| `maya_fluid__list_fluid_containers` | List all fluid containers |
| `maya_fluid__delete_fluid_container` | Delete a fluid container |

### maya-grooming (5 actions)

Hair/fur groom management (XGen Interactive Groom).

| Action | Description |
|--------|-------------|
| `maya_grooming__create_groom` | Create a new interactive groom |
| `maya_grooming__delete_groom` | Delete a groom |
| `maya_grooming__list_groomables` | List all groomable meshes |
| `maya_grooming__export_groom_cache` | Export groom to a Alembic cache |
| `maya_grooming__convert_groom_to_curves` | Convert groom to NURBS curves |

### maya-muscle (5 actions)

Maya Muscle deformation system.

| Action | Description |
|--------|-------------|
| `maya_muscle__create_muscle_capsule` | Create a muscle capsule object |
| `maya_muscle__attach_muscle_to_skin` | Attach a muscle to a skin mesh |
| `maya_muscle__set_muscle_attribute` | Set muscle simulation attributes |
| `maya_muscle__list_muscles` | List all muscles in the scene |
| `maya_muscle__delete_muscle` | Delete a muscle object |

### maya-nparticles (5 actions)

nParticle simulation system.

| Action | Description |
|--------|-------------|
| `maya_nparticles__create_nparticle_system` | Create an nParticle system |
| `maya_nparticles__emit_particles` | Emit particles from an emitter |
| `maya_nparticles__set_nparticle_attribute` | Set nParticle solver attributes |
| `maya_nparticles__list_nparticle_systems` | List all nParticle systems |
| `maya_nparticles__delete_nparticle_system` | Delete an nParticle system |

### maya-ocean (5 actions)

Maya Ocean simulation.

| Action | Description |
|--------|-------------|
| `maya_ocean__create_ocean` | Create an ocean shader plane |
| `maya_ocean__create_wake` | Create a wake/boat-trail effect |
| `maya_ocean__set_ocean_attribute` | Set ocean wave and foam attributes |
| `maya_ocean__list_oceans` | List all ocean shaders in the scene |
| `maya_ocean__delete_ocean` | Delete an ocean shader |

### maya-paint-effects (5 actions)

Maya Paint Effects stroke and brush management.

| Action | Description |
|--------|-------------|
| `maya_paint_effects__create_stroke` | Create a Paint Effects stroke |
| `maya_paint_effects__set_brush_attribute` | Set brush shape and behavior attributes |
| `maya_paint_effects__convert_stroke_to_poly` | Convert a stroke to polygon geometry |
| `maya_paint_effects__list_strokes` | List all Paint Effects strokes |
| `maya_paint_effects__delete_stroke` | Delete a Paint Effects stroke |

### maya-toon (5 actions)

Maya Toon shader and outline management.

| Action | Description |
|--------|-------------|
| `maya_toon__create_toon_outline` | Create a toon outline on an object |
| `maya_toon__assign_toon_shader` | Assign a toon shader to an object |
| `maya_toon__set_toon_attribute` | Set toon line and fill attributes |
| `maya_toon__list_toon_lines` | List all toon line nodes |
| `maya_toon__delete_toon_line` | Delete a toon line node |

