# Action List

All built-in actions are organized into skill packages. Each action becomes an MCP tool with the naming convention:

```
{skill_name.replace("-", "_")}__{script_stem}
```

## Scene Management (`maya-scene`)

Manage the Maya scene lifecycle, object hierarchy, and scene state.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| New Scene | `maya_scene__new_scene` | Create a new empty Maya scene |
| Save Scene | `maya_scene__save_scene` | Save the current scene to disk |
| Open Scene | `maya_scene__open_scene` | Open a Maya scene file (.ma, .mb) |
| Export Scene | `maya_scene__export_scene` | Export the entire scene to a file |
| List Objects | `maya_scene__list_objects` | List DAG objects with optional type filter |
| Get Selection | `maya_scene__get_selection` | Return the current selection list |
| Set Selection | `maya_scene__set_selection` | Set the active selection |
| Select by Type | `maya_scene__select_by_type` | Select all objects of a given Maya type |
| Get Session Info | `maya_scene__get_session_info` | Maya version, scene path, FPS, object count |
| Get Scene Info | `maya_scene__get_scene_info` | Hierarchical DAG description of the scene |
| Group Objects | `maya_scene__group_objects` | Group objects under a new group node |
| Parent Object | `maya_scene__parent_object` | Set or clear the parent of an object |
| Duplicate Object | `maya_scene__duplicate_object` | Duplicate an object in the scene |
| Freeze Transforms | `maya_scene__freeze_transforms` | Freeze the transforms of an object |
| Center Pivot | `maya_scene__center_pivot` | Center pivot to bounding box center |
| Get Bounding Box | `maya_scene__get_bounding_box` | Query the world-space bounding box |
| Set Visibility | `maya_scene__set_visibility` | Show or hide an object |
| Lock Object | `maya_scene__lock_object` | Lock/unlock transform attributes |
| Set Frame Rate | `maya_scene__set_frame_rate` | Change the scene playback frame rate |
| List Cameras | `maya_scene__list_cameras` | List all cameras in the scene |
| Create Locator | `maya_scene__create_locator` | Create a Maya locator node |

## Geometry & Primitives (`maya-primitives`)

Create polygon primitives and manage object transforms.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Create Sphere | `maya_primitives__create_sphere` | Create a polygon sphere |
| Create Cube | `maya_primitives__create_cube` | Create a polygon cube |
| Create Cylinder | `maya_primitives__create_cylinder` | Create a polygon cylinder |
| Create Plane | `maya_primitives__create_plane` | Create a polygon plane |
| Delete Objects | `maya_primitives__delete_objects` | Delete objects from the scene |
| Set Transform | `maya_primitives__set_transform` | Set translate/rotate/scale on an object |
| Get Transform | `maya_primitives__get_transform` | Get translate/rotate/scale of an object |
| Rename Object | `maya_primitives__rename_object` | Rename an object in the scene |

## Animation (`maya-animation`)

Full animation pipeline: keyframes, curves, timeline, simulation baking.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Set Keyframe | `maya_animation__set_keyframe` | Set a keyframe on an object attribute |
| Get Keyframes | `maya_animation__get_keyframes` | Get all keyframe times for an object/attribute |
| Set Timeline | `maya_animation__set_timeline` | Set the playback and animation range |
| Get Current Time | `maya_animation__get_current_time` | Get the current frame number |
| Set Current Time | `maya_animation__set_current_time` | Set the current frame number |
| Delete Keyframes | `maya_animation__delete_keyframes` | Delete keyframes in an optional frame range |
| Bake Simulation | `maya_animation__bake_simulation` | Bake simulation/constraints to keyframes |
| Bake Constraints | `maya_animation__bake_constraints` | Bake constraint-driven animation |
| List Anim Curves | `maya_animation__list_animation_curves` | List all animCurve nodes driving an object |
| Set Curve Tangent | `maya_animation__set_animation_curve_tangent` | Set tangent type on keyframes |
| Export Anim Curves | `maya_animation__export_animation_curves` | Export animation curves to .anim file |
| Import Anim Curves | `maya_animation__import_animation_curves` | Import animation curves from a file |
| Query Time Info | `maya_animation__query_scene_time_info` | Query current scene time and playback settings |

## Cameras (`maya-cameras`)

Create and configure Maya cameras.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Create Camera | `maya_cameras__create_camera` | Create a camera with position, rotation, focal length |
| Set Camera Attribute | `maya_cameras__set_camera_attribute` | Set focalLength, nearClipPlane, etc. |
| Get Camera Info | `maya_cameras__get_camera_info` | Focal length, clipping, aperture and transform |
| Set Active Camera | `maya_cameras__set_active_camera` | Set the active viewport camera |

## Lighting (`maya-lighting`)

Create and manage Maya lights.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Create Light | `maya_lighting__create_light` | Create directional/point/spot/area/ambient light |
| Set Light Attribute | `maya_lighting__set_light_attribute` | Set intensity, color, shadow attributes |
| List Lights | `maya_lighting__list_lights` | List all lights with type and intensity |

## Render (`maya-render`)

Render settings and viewport capture.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Set Render Settings | `maya_render__set_render_settings` | Set resolution, frame range, renderer |
| Get Render Settings | `maya_render__get_render_settings` | Query current render settings |
| Playblast / Capture | `maya_render__playblast` | Capture viewport as base64-encoded PNG |

## Materials (`maya-materials`)

Create and manage shading materials.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Create Material | `maya_materials__create_material` | Create Lambert/Blinn/Phong/Arnold material |
| Assign Material | `maya_materials__assign_material` | Assign material to objects |
| Set Material Attr | `maya_materials__set_material_attribute` | Set material color, roughness, etc. |
| List Materials | `maya_materials__list_materials` | List all scene materials |

## Mesh Operations (`maya-mesh-ops`)

Polygon mesh operations — subdivision, boolean, cleanup.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Subdivide | `maya_mesh_ops__subdivide` | Subdivide a polygon mesh |
| Boolean | `maya_mesh_ops__boolean_operation` | Boolean union/difference/intersection |
| Cleanup | `maya_mesh_ops__cleanup_mesh` | Run polygon cleanup on a mesh |
| Extract Face | `maya_mesh_ops__extract_face` | Extract selected faces to a new mesh |
| Combine | `maya_mesh_ops__combine_meshes` | Combine multiple meshes into one |
| Separate | `maya_mesh_ops__separate_meshes` | Separate a combined mesh |
| Fill Hole | `maya_mesh_ops__fill_hole` | Fill an open hole in a mesh |
| Mirror | `maya_mesh_ops__mirror_mesh` | Mirror a mesh across an axis |
| Triangulate | `maya_mesh_ops__triangulate` | Convert all faces to triangles |
| Quadrangulate | `maya_mesh_ops__quadrangulate` | Convert triangles to quads where possible |
| Smooth | `maya_mesh_ops__smooth_mesh` | Apply smooth mesh preview |
| Get Poly Info | `maya_mesh_ops__get_poly_info` | Query vertex/edge/face count |

## UV Operations (`maya-uv-ops`)

UV layout creation and editing.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Planar Project | `maya_uv_ops__planar_projection` | Apply planar UV projection |
| Cylindrical Project | `maya_uv_ops__cylindrical_projection` | Apply cylindrical UV projection |
| Spherical Project | `maya_uv_ops__spherical_projection` | Apply spherical UV projection |
| Auto Unwrap | `maya_uv_ops__auto_unwrap` | Automatic UV unfold |
| Normalize UVs | `maya_uv_ops__normalize_uvs` | Normalize UVs to 0–1 space |
| Flip UVs | `maya_uv_ops__flip_uvs` | Flip UVs horizontally or vertically |
| Rotate UVs | `maya_uv_ops__rotate_uvs` | Rotate UVs by a given angle |
| Layout UVs | `maya_uv_ops__layout_uvs` | Pack UV shells into the 0–1 tile |

## Rigging (`maya-rigging`)

Joints, IK, skin clusters, and constraints.

| Action | Tool Name | Description |
|--------|-----------|-------------|
| Create Joint | `maya_rigging__create_joint` | Create a joint at a given position |
| Parent Joint | `maya_rigging__parent_joint` | Parent one joint under another |
| Create IK Handle | `maya_rigging__create_ik_handle` | Create an IK handle between joints |
| Bind Skin | `maya_rigging__bind_skin` | Bind a mesh to a skeleton |
| Unbind Skin | `maya_rigging__unbind_skin` | Detach a skin cluster |
| Set Skin Weights | `maya_rigging__set_skin_weights` | Set skin weights on a vertex |
| Get Skin Weights | `maya_rigging__get_skin_weights` | Query skin weights for a vertex |
| Create Constraint | `maya_rigging__create_constraint` | Create parent/point/orient/scale constraint |
| Remove Constraint | `maya_rigging__remove_constraint` | Remove a constraint from an object |
| Create Blend Shape | `maya_rigging__create_blend_shape` | Create a blend shape deformer |
| Set Blend Shape Weight | `maya_rigging__set_blend_shape_weight` | Set a blend shape target weight |

## Additional Skill Packages

The following skill packages are also included. Documentation will be expanded in future iterations:

| Package | Description |
|---------|-------------|
| `maya-attributes` | Node attribute inspection and editing |
| `maya-constraints` | Basic constraint operations |
| `maya-constraints-advanced` | Advanced constraint setups |
| `maya-deformers` | Lattice, cluster, wrap and other deformers |
| `maya-display` | Display layers creation and management |
| `maya-dynamics` | Rigid body, nCloth, nHair dynamics |
| `maya-expressions` | Maya expression node management |
| `maya-namespaces` | Namespace creation, merge and removal |
| `maya-node-graph` | Hypershade / node graph operations |
| `maya-references` | File reference management |
| `maya-render-layers` | Render layer creation and override |
| `maya-selection` | Selection set and quick-select operations |
| `maya-sets` | Object set creation and membership |
| `maya-texture-bake` | Texture baking to UV maps |
| `maya-xform-utils` | Advanced transform utilities |
| `maya-xgen` | XGen hair and fur system |
| `maya-arnold-aov` | Arnold AOV configuration |
| `maya-hdri` | HDRI environment setup |
| `maya-mash` | MASH motion graphics network |
| `maya-material-library` | Material library management |
| `maya-light-rig` | Light rig creation templates |
| `maya-bifrost` | Bifrost graph operations |
| `maya-nparticles` | nParticle system |
| `maya-paint-effects` | Paint Effects brush strokes |
| `maya-toon` | Toon shader setup |
| `maya-audio` | Audio track management |
| `maya-cache` | Geometry cache (Alembic / MCC) |
| `maya-color-grading` | Color management settings |
| `maya-gpu-cache` | GPU cache import/export |
| `maya-instancer` | Particle instancer |
| `maya-rig-utils` | Rig helper utilities |
| `maya-skinning-utils` | Skin weight copy/mirror/transfer |
| `maya-spline-ik` | Spline IK chain setup |
| `maya-blend-shape-utils` | Blend shape utility operations |
| `maya-camera-sequence` | Camera sequencer |
| `maya-annotation` | Maya annotation nodes |
| `maya-scene-utils` | Scene utility helpers |
| `maya-pose-library` | Pose library management |
| `maya-shot-export` | Shot-based export pipeline |
| `maya-render-farm` | Render farm submission |
| `maya-render-passes` | Render pass configuration |
| `maya-vertex-color` | Vertex color paint and query |
