"""Batch-add ``prompt=`` to maya_success() calls that are missing it.

Run from the repo root:
    python tools/add_prompts.py
"""
from __future__ import annotations

import os
import re
import sys

SKILL_ROOT = os.path.join("src", "dcc_mcp_maya", "skills")

# ---------------------------------------------------------------------------
# Prompt library keyed by (skill_dir, script_stem)  or  (script_stem,)
# ---------------------------------------------------------------------------
# The outer dict key is the skill directory name (e.g. "maya-animation").
# The inner dict key is the script stem (filename without .py).
# Value is the prompt string.
PROMPT_MAP: dict[str, dict[str, str]] = {
    "maya-animation": {
        "bake_constraints": "Use list_animation_curves or set_keyframe to adjust the baked keys.",
        "bake_simulation": "Use delete_keyframes to trim unwanted frames, or export_animation_curves to save.",
        "delete_keyframes": "Use set_keyframe to add new keys, or get_keyframes to verify the result.",
        "export_animation_curves": "Use import_animation_curves to restore the curves on another rig.",
        "get_current_time": "Use set_current_time to seek to a specific frame.",
        "get_keyframes": "Use set_keyframe to modify keys or delete_keyframes to remove them.",
        "import_animation_curves": "Use list_animation_curves to verify the imported curves.",
        "list_animation_curves": "Use export_animation_curves to save or delete_keyframes to clean up.",
        "query_scene_time_info": "Use set_timeline to adjust the frame range.",
        "set_animation_curve_tangent": "Use bake_simulation to flatten or get_keyframes to inspect.",
        "set_current_time": "Use get_current_time to verify or set_keyframe to record the pose.",
        "set_keyframe": "Use get_keyframes to verify or bake_simulation to collapse to keys.",
        "set_timeline": "Use set_current_time to navigate the new range.",
    },
    "maya-annotation": {
        "create_annotation": "Use update_annotation to change text or list_annotations to review all.",
        "delete_annotation": "Use list_annotations to check remaining annotations.",
        "list_annotations": "Use update_annotation to edit or delete_annotation to remove one.",
        "update_annotation": "Use list_annotations to confirm the change.",
    },
    "maya-arnold-aov": {
        "add_aov": "Use enable_aov to toggle or list_aovs to review the full AOV list.",
        "delete_aov": "Use list_aovs to verify the AOV was removed.",
        "enable_aov": "Use list_aovs to see all active AOVs.",
        "list_aovs": "Use add_aov to create new passes or enable_aov to toggle existing ones.",
        "set_aov_driver": "Use list_aovs to verify the driver was applied.",
    },
    "maya-attributes": {
        "add_attribute": "Use set_attribute to assign a value or list_custom_attributes to review.",
        "connect_attributes": "Use list_node_connections in maya-utility to inspect the graph.",
        "delete_attribute": "Use list_custom_attributes to verify removal.",
        "get_attribute": "Use set_attribute to modify the value.",
        "list_custom_attributes": "Use add_attribute or delete_attribute to manage them.",
        "lock_attribute": "Use unlock_attribute to undo or get_attribute to verify.",
        "set_attribute": "Use get_attribute to verify the new value.",
        "unlock_attribute": "Use set_attribute to assign a value.",
    },
    "maya-audio": {
        "import_audio": "Use set_timeline_audio to attach the sound to the Maya timeline.",
        "list_audio": "Use set_timeline_audio or remove_audio to manage audio nodes.",
        "remove_audio": "Use import_audio to load a replacement.",
        "set_timeline_audio": "Use list_audio to confirm which sound is active.",
    },
    "maya-bifrost": {
        "add_bifrost_graph": "Use set_bifrost_property to configure the graph.",
        "connect_bifrost_ports": "Use list_bifrost_graphs to verify the connection.",
        "list_bifrost_graphs": "Use add_bifrost_graph to create more or connect_bifrost_ports to wire nodes.",
        "set_bifrost_property": "Use list_bifrost_graphs to confirm the change.",
    },
    "maya-blend-shape-utils": {
        "create_blend_shape": "Use set_blend_shape_weight to drive the blend or list_blend_shapes to review.",
        "get_blend_shape_weights": "Use set_blend_shape_weight to adjust individual targets.",
        "list_blend_shapes": "Use get_blend_shape_weights or set_blend_shape_weight to manage targets.",
        "set_blend_shape_weight": "Use get_blend_shape_weights to verify or create_blend_shape to add more.",
    },
    "maya-cache": {
        "attach_geometry_cache": "Use list_geometry_caches to confirm it is attached.",
        "create_geometry_cache": "Use attach_geometry_cache to re-link or list_geometry_caches to verify.",
        "delete_geometry_cache": "Use create_geometry_cache to re-bake if needed.",
        "list_geometry_caches": "Use attach_geometry_cache or delete_geometry_cache to manage entries.",
    },
    "maya-cameras": {
        "create_camera": "Use set_camera_attribute to adjust focal length or framing.",
        "delete_camera": "Use list_cameras to confirm deletion.",
        "get_camera_info": "Use set_camera_attribute to modify properties.",
        "list_cameras": "Use get_camera_info or create_camera to manage cameras.",
        "set_active_camera": "Use get_camera_info to inspect the active camera settings.",
        "set_camera_attribute": "Use get_camera_info to verify the change.",
    },
    "maya-camera-sequence": {
        "create_shot": "Use list_shots to review the sequence or set_shot_range to adjust timing.",
        "delete_shot": "Use list_shots to verify the shot was removed.",
        "list_shots": "Use create_shot or set_shot_range to manage the sequence.",
        "set_shot_range": "Use list_shots to confirm the updated timing.",
    },
    "maya-cloth-sim": {
        "bake_cloth_cache": "Use attach_geometry_cache to re-link or list_ncloth_objects to verify.",
        "create_ncloth": "Use set_ncloth_attribute to tune stiffness/damping, then simulate.",
        "list_ncloth_objects": "Use set_ncloth_attribute to tune or bake_cloth_cache to export.",
        "set_ncloth_attribute": "Use list_ncloth_objects to verify the changed value.",
    },
    "maya-color-grading": {
        "apply_gamma_correction": "Use set_rendering_space to match the colour space pipeline.",
        "get_color_management_info": "Use set_rendering_space or set_view_transform to adjust.",
        "set_rendering_space": "Use get_color_management_info to confirm the change.",
        "set_view_transform": "Use get_color_management_info to verify the active LUT.",
    },
    "maya-constraints": {
        "add_aim_constraint": "Use bake_constraint to flatten or get_constraint_weights to inspect.",
        "add_orient_constraint": "Use bake_constraint to flatten or get_constraint_weights to inspect.",
        "add_parent_constraint": "Use bake_constraint to collapse or get_constraint_weights to inspect.",
        "add_point_constraint": "Use bake_constraint to flatten or get_constraint_weights to inspect.",
        "add_scale_constraint": "Use bake_constraint to flatten or get_constraint_weights to inspect.",
        "list_constraints": "Use bake_constraint or get_constraint_weights to manage the listed nodes.",
        "remove_constraint": "Use list_constraints to verify the constraint was removed.",
    },
    "maya-constraints-advanced": {
        "add_pole_vector_constraint": "Use set_constraint_weight to blend or bake_constraint to bake.",
        "bake_constraint": "Use delete_keyframes to trim or export_animation_curves to archive.",
        "get_constraint_weights": "Use set_constraint_weight to update individual driver blends.",
        "set_constraint_weight": "Use get_constraint_weights to verify the new weight distribution.",
    },
    "maya-deformers": {
        "add_cluster": "Use set_attribute to weight or parent_object to organise.",
        "add_lattice": "Use set_attribute to adjust divisions or delete to remove.",
        "add_wire_deformer": "Use set_attribute to tune influence or list_deformers to review.",
        "add_wrap_deformer": "Use set_attribute to tune or list_deformers to verify.",
        "list_deformers": "Use set_attribute or delete_object to manage the listed deformers.",
        "paint_deformer_weights": "Use list_deformers to confirm or set_attribute to further tweak.",
        "remove_deformer": "Use list_deformers to verify removal.",
    },
    "maya-display": {
        "add_to_display_layer": "Use list_display_layers to review membership.",
        "create_display_layer": "Use add_to_display_layer to populate or set_display_layer_attribute to adjust.",
        "delete_display_layer": "Use list_display_layers to confirm deletion.",
        "list_display_layers": "Use create_display_layer or set_display_layer_attribute to manage layers.",
        "remove_from_display_layer": "Use list_display_layers to verify the object was moved to defaultLayer.",
        "set_display_layer_attribute": "Use list_display_layers to confirm the change.",
    },
    "maya-dynamics": {
        "add_field_to_emitter": "Use list_particle_systems to verify the field connection.",
        "add_turbulence": "Use list_particle_systems to see the effect.",
        "bake_particle_cache": "Use list_particle_systems to verify or attach_geometry_cache to manage.",
        "connect_emitter_to_nucleus": "Use create_ncloth or list_nparticle_systems to verify.",
        "create_emitter": "Use create_particle_system or add_field_to_emitter to complete the setup.",
        "create_nrigid": "Use list_ncloth_objects to verify or set_ncloth_attribute to tune.",
        "create_nucleus": "Use create_ncloth or create_nparticle_emitter to attach solvers.",
        "create_particle_system": "Use add_field_to_emitter or bake_particle_cache to manage.",
        "list_particle_systems": "Use add_field_to_emitter or bake_particle_cache to manage.",
        "set_emitter_attribute": "Use list_particle_systems to verify the changed value.",
    },
    "maya-export-preset": {
        "delete_export_preset": "Use list_export_presets to confirm deletion.",
        "list_export_presets": "Use load_export_preset to apply or save_export_preset to create new.",
        "load_export_preset": "Use export_shot_fbx or export_shot_alembic to run the export.",
        "save_export_preset": "Use list_export_presets to verify it was saved.",
    },
    "maya-expressions": {
        "create_expression": "Use list_expressions to verify or edit_expression to modify.",
        "delete_expression": "Use list_expressions to confirm deletion.",
        "edit_expression": "Use list_expressions to verify the updated expression.",
        "list_expressions": "Use edit_expression or delete_expression to manage them.",
    },
    "maya-fluid": {
        "create_fluid_container": "Use set_fluid_attribute to configure density/velocity or simulate.",
        "delete_fluid_container": "Use list_fluid_containers to confirm deletion.",
        "list_fluid_containers": "Use set_fluid_attribute or delete_fluid_container to manage.",
        "set_fluid_attribute": "Use list_fluid_containers to verify the changed value.",
    },
    "maya-gpu-cache": {
        "export_gpu_cache": "Use import_gpu_cache to load the .abc into another scene.",
        "import_gpu_cache": "Use list_gpu_caches to verify or refresh_gpu_cache if needed.",
        "list_gpu_caches": "Use refresh_gpu_cache to reload or export_gpu_cache to archive.",
        "refresh_gpu_cache": "Use list_gpu_caches to confirm the update.",
    },
    "maya-grooming": {
        "add_nhair_cache": "Use list_hair_systems to verify the cache was attached.",
        "create_nhair_system": "Use set_nhair_attribute to tune length/curl or add_nhair_cache to bake.",
        "list_hair_systems": "Use set_nhair_attribute or add_nhair_cache to manage the listed systems.",
        "set_nhair_attribute": "Use list_hair_systems to verify the changed value.",
    },
    "maya-hdri": {
        "list_hdri_nodes": "Use set_hdri_exposure or set_hdri_rotation to adjust the listed domes.",
        "load_hdri": "Use set_hdri_exposure or set_hdri_rotation to fine-tune the lighting.",
        "set_hdri_exposure": "Use list_hdri_nodes to confirm or render_frame to preview.",
        "set_hdri_rotation": "Use set_hdri_exposure or render_frame to verify the new orientation.",
    },
    "maya-instancer": {
        "add_instance_object": "Use list_instancers to verify the geometry was added.",
        "create_instancer": "Use add_instance_object to add more geometry or set_instancer_attribute to tune.",
        "list_instancers": "Use add_instance_object or set_instancer_attribute to manage.",
        "set_instancer_attribute": "Use list_instancers to confirm the change.",
    },
    "maya-lighting": {
        "add_light_link": "Use list_light_links to verify or remove_light_link to undo.",
        "create_area_light": "Use set_light_attribute to adjust intensity/colour.",
        "create_directional_light": "Use set_light_attribute to adjust intensity/colour.",
        "create_point_light": "Use set_light_attribute to adjust intensity/colour.",
        "create_spot_light": "Use set_light_attribute to adjust cone angle/intensity.",
        "delete_light": "Use list_lights to confirm deletion.",
        "list_light_links": "Use add_light_link or remove_light_link to manage.",
        "list_lights": "Use set_light_attribute or delete_light to manage the listed lights.",
        "remove_light_link": "Use list_light_links to verify removal.",
        "set_light_attribute": "Use list_lights to verify or render_frame to preview the change.",
    },
    "maya-light-rig": {
        "create_hdri_dome": "Use set_hdri_exposure to adjust or list_hdri_nodes to verify.",
        "create_three_point_rig": "Use set_light_rig_intensity to adjust or list_light_rigs to review.",
        "list_light_rigs": "Use set_light_rig_intensity to adjust or delete_light to remove members.",
        "set_light_rig_intensity": "Use list_light_rigs to verify or render_frame to preview.",
    },
    "maya-mash": {
        "create_network": "Use set_mash_attribute to configure or list_networks to verify.",
        "delete_network": "Use list_networks to confirm deletion.",
        "list_networks": "Use set_mash_attribute or delete_network to manage the listed networks.",
        "set_mash_attribute": "Use list_networks to confirm the change.",
    },
    "maya-material-library": {
        "delete_material_preset": "Use list_materials to confirm deletion.",
        "list_materials": "Use load_material to apply a preset or save_material to add a new one.",
        "load_material": "Use assign_material to attach it to objects.",
        "save_material": "Use list_materials to verify it was saved.",
    },
    "maya-materials": {
        "assign_material": "Use set_material_attribute to fine-tune the material properties.",
        "create_material": "Use assign_material to apply to objects or set_material_attribute to configure.",
        "get_material_connections": "Use set_material_attribute to modify or assign_material to reassign.",
        "get_shader_assignment": "Use assign_material to change or set_material_attribute to adjust.",
        "list_materials": "Use assign_material or set_material_attribute to manage the listed shaders.",
        "list_shading_groups": "Use assign_material or get_shader_assignment to inspect.",
        "reset_to_default_material": "Use create_material and assign_material to set a new shader.",
        "set_material_attribute": "Use get_material_connections to verify or render_frame to preview.",
    },
    "maya-mesh-ops": {
        "apply_subdivision": "Use get_poly_count to verify the increased density.",
        "cleanup_mesh": "Use get_poly_count or select_by_material to inspect the result.",
        "combine_meshes": "Use cleanup_mesh or assign_material to finalise the combined mesh.",
        "create_proxy_mesh": "Use swap_proxy in maya-proxy-mesh to toggle between proxy and hi-res.",
        "extract_faces": "Use combine_meshes or cleanup_mesh to post-process.",
        "get_mesh_edge_info": "Use merge_vertices or cleanup_mesh to fix edge issues.",
        "get_poly_count": "Use apply_subdivision or cleanup_mesh to adjust the geometry.",
        "merge_vertices": "Use cleanup_mesh to verify or get_poly_count to check the result.",
        "mirror_mesh": "Use freeze_transforms in maya-xform-utils to clean up.",
        "select_by_material": "Use assign_material to replace or list_materials to inspect.",
        "separate_mesh": "Use combine_meshes to undo or cleanup_mesh on each piece.",
        "triangulate": "Use export_shot_fbx or get_poly_count to verify the result.",
    },
    "maya-mocap": {
        "bake_mocap_to_rig": "Use clean_mocap_keys to reduce redundant keys.",
        "clean_mocap_keys": "Use export_animation_curves to archive the cleaned animation.",
        "create_hik_definition": "Use bake_mocap_to_rig to retarget motion data.",
        "import_mocap": "Use create_hik_definition to define the skeleton mapping.",
    },
    "maya-muscle": {
        "apply_muscle_skin": "Use set_muscle_attribute to tune or list_muscles to review.",
        "create_muscle_capsule": "Use apply_muscle_skin to attach or set_muscle_attribute to tune.",
        "list_muscles": "Use set_muscle_attribute or apply_muscle_skin to manage.",
        "set_muscle_attribute": "Use list_muscles to verify the change.",
    },
    "maya-namespaces": {
        "create_namespace": "Use list_namespaces to verify or rename_namespace to adjust.",
        "list_namespaces": "Use create_namespace, rename_namespace, or remove_namespace to manage.",
        "remove_namespace": "Use list_namespaces to confirm the namespace was merged.",
        "rename_namespace": "Use list_namespaces to verify the new name.",
    },
    "maya-node-graph": {
        "connect_nodes": "Use list_node_connections to verify or disconnect_nodes to undo.",
        "create_node": "Use connect_nodes or set_attribute to configure the new node.",
        "delete_node": "Use list_node_connections to check upstream/downstream before deleting.",
        "disconnect_nodes": "Use connect_nodes to rewire or list_node_connections to inspect.",
        "list_node_connections": "Use connect_nodes or disconnect_nodes to manage the graph.",
    },
    "maya-nparticles": {
        "add_field_to_nparticles": "Use set_nparticle_attribute to tune or list_nparticle_systems to verify.",
        "create_nparticle_emitter": "Use add_field_to_nparticles to add forces or set_nparticle_attribute to tune.",
        "list_nparticle_systems": "Use set_nparticle_attribute or add_field_to_nparticles to manage.",
        "set_nparticle_attribute": "Use list_nparticle_systems to verify the changed value.",
    },
    "maya-ocean": {
        "add_ocean_wake": "Use set_ocean_attribute to tune or list_ocean_surfaces to verify.",
        "create_ocean": "Use set_ocean_attribute to adjust wave height/speed.",
        "list_ocean_surfaces": "Use set_ocean_attribute or add_ocean_wake to manage.",
        "set_ocean_attribute": "Use list_ocean_surfaces to verify the change.",
    },
    "maya-paint-effects": {
        "attach_stroke_to_surface": "Use list_strokes to verify or delete_stroke to remove.",
        "create_stroke": "Use list_strokes to review or delete_stroke to clean up.",
        "delete_stroke": "Use list_strokes to confirm deletion.",
        "list_strokes": "Use delete_stroke to remove or attach_stroke_to_surface to scatter.",
    },
    "maya-pipeline": {
        "get_asset_metadata": "Use tag_asset_metadata to update or publish_asset to export.",
        "publish_asset": "Use get_asset_metadata to verify the published tags.",
        "set_project": "Use publish_asset or save_scene to work within the new project.",
        "tag_asset_metadata": "Use get_asset_metadata to verify the stored metadata.",
    },
    "maya-pose-library": {
        "list_poses": "Use load_pose to apply a pose or save_pose to add a new one.",
        "load_pose": "Use mirror_pose to flip left/right or save_pose to capture the result.",
        "mirror_pose": "Use load_pose to apply the mirrored file to the scene.",
        "save_pose": "Use list_poses to verify or load_pose to restore.",
    },
    "maya-primitives": {
        "create_cone": "Use set_transform to position or assign_material to shade.",
        "create_cube": "Use set_transform to position or assign_material to shade.",
        "create_cylinder": "Use set_transform to position or assign_material to shade.",
        "create_plane": "Use set_transform to position or assign_material to shade.",
        "create_sphere": "Use set_transform to position or assign_material to shade.",
        "create_torus": "Use set_transform to position or assign_material to shade.",
    },
    "maya-proxy-mesh": {
        "create_proxy": "Use swap_proxy to switch between proxy and hi-res.",
        "list_proxies": "Use swap_proxy or set_proxy_attribute to manage the listed proxies.",
        "set_proxy_attribute": "Use list_proxies to verify the change.",
        "swap_proxy": "Use list_proxies to confirm the current proxy state.",
    },
    "maya-references": {
        "create_reference": "Use list_references to verify or reload_reference if the file changes.",
        "import_reference": "Use list_references to confirm the reference was imported.",
        "list_references": "Use reload_reference or remove_reference to manage the listed entries.",
        "reload_reference": "Use list_references to confirm the reference status.",
        "remove_reference": "Use list_references to verify removal.",
    },
    "maya-render": {
        "capture_viewport": "Use render_frame for final-quality output.",
        "playblast": "Use render_frame for a final-quality render.",
        "render_frame": "Use set_render_settings to adjust resolution or frame range.",
        "set_render_settings": "Use render_frame to test the new settings.",
    },
    "maya-render-farm": {
        "get_render_job_status": "Use submit_to_deadline to resubmit or write_render_job to modify.",
        "submit_to_deadline": "Use get_render_job_status to monitor progress.",
        "validate_scene_for_farm": "Use set_render_settings to fix errors, then resubmit.",
        "write_render_job": "Use submit_to_deadline to dispatch or validate_scene_for_farm first.",
    },
    "maya-render-layers": {
        "add_to_render_layer": "Use list_render_layers to verify membership.",
        "create_render_layer": "Use add_to_render_layer to populate or set_render_layer_attribute to adjust.",
        "delete_render_layer": "Use list_render_layers to confirm deletion.",
        "list_render_layers": "Use create_render_layer or add_to_render_layer to manage.",
        "remove_from_render_layer": "Use list_render_layers to verify the change.",
        "set_current_render_layer": "Use render_frame to test the active layer.",
        "set_render_layer_attribute": "Use list_render_layers to verify the change.",
    },
    "maya-render-passes": {
        "create_render_pass": "Use enable_render_pass to activate or list_render_passes to review.",
        "enable_render_pass": "Use list_render_passes to verify or render_frame to preview.",
        "list_render_passes": "Use create_render_pass or enable_render_pass to manage.",
        "set_render_pass_output": "Use list_render_passes to confirm or render_frame to test.",
    },
    "maya-rigging": {
        "add_ik_handle": "Use add_space_switch in maya-rig-utils or set_attribute to tune.",
        "bind_skin": "Use normalize_skin_weights or copy_skin_weights to manage weighting.",
        "create_joint": "Use bind_skin or add_ik_handle to complete the rig.",
        "list_joints": "Use create_joint or bind_skin to build the skeleton.",
        "orient_joints": "Use list_joints to verify or bind_skin to proceed.",
        "set_joint_limits": "Use list_joints to verify or add_ik_handle to wire the chain.",
    },
    "maya-rig-utils": {
        "add_space_switch": "Use set_constraint_weight in maya-constraints-advanced to test.",
        "connect_attributes": "Use list_node_connections in maya-utility to verify.",
        "create_control_curve": "Use add_space_switch or lock_hide_attributes to finish the control.",
        "lock_hide_attributes": "Use create_control_curve to add more controls.",
    },
    "maya-scene": {
        "export_selection": "Use import_file to load the exported asset in another scene.",
        "get_scene_info": "Use set_transform or assign_material to modify listed objects.",
        "import_file": "Use list_objects or get_scene_info to inspect the imported content.",
        "open_scene": "Use get_scene_info to inspect the scene contents.",
        "save_scene": "Use export_selection to share individual assets.",
    },
    "maya-scene-assembly": {
        "add_assembly_representation": "Use list_assemblies to review or create_assembly_reference to instance.",
        "create_assembly_definition": "Use add_assembly_representation to populate.",
        "create_assembly_reference": "Use list_assemblies to verify or set_attribute to configure.",
        "list_assemblies": "Use create_assembly_reference or add_assembly_representation to manage.",
    },
    "maya-scene-utils": {
        "check_scene_health": "Use clean_scene in maya-utility to fix the listed issues.",
        "export_scene_report": "Use check_scene_health or clean_scene to act on the findings.",
        "list_scene_nodes": "Use delete_object or set_attribute to manage the listed nodes.",
        "optimize_scene": "Use check_scene_health to verify or save_scene to archive.",
    },
    "maya-scripting": {
        "execute_mel": "Use execute_python for more complex operations or list_mel_procedures to explore.",
        "execute_python": "Use execute_mel for MEL-only commands.",
        "get_script_node": "Use execute_mel or execute_python to inspect behaviour.",
        "list_mel_procedures": "Use execute_mel to call a discovered procedure.",
    },
    "maya-selection": {
        "deselect_all": "Use select_objects to start a new selection.",
        "get_selection": "Use set_transform or assign_material to operate on selected objects.",
        "invert_selection": "Use get_selection to inspect or deselect_all to clear.",
        "select_all": "Use get_selection to inspect all selected objects.",
        "select_by_name": "Use get_selection to verify or set_transform to operate on the result.",
        "select_by_type": "Use get_selection or assign_material to work with the selection.",
        "select_hierarchy": "Use get_selection to inspect or set_transform to operate.",
        "select_objects": "Use get_selection to verify or set_transform to modify.",
    },
    "maya-sets": {
        "add_to_set": "Use list_set_members to verify membership.",
        "create_set": "Use add_to_set to populate or list_sets to review.",
        "delete_set": "Use list_sets to confirm deletion.",
        "list_set_members": "Use add_to_set or remove_from_set to manage membership.",
        "list_sets": "Use add_to_set or delete_set to manage the listed sets.",
        "remove_from_set": "Use list_set_members to verify removal.",
    },
    "maya-shot-export": {
        "export_camera": "Use list_cameras to verify or import_file to reload in another scene.",
        "export_shot_alembic": "Use import_file or create_reference to load the .abc in another scene.",
        "export_shot_fbx": "Use import_file to load the .fbx in another application.",
        "get_shot_info": "Use set_render_settings to align or export_shot_fbx to archive.",
    },
    "maya-skinning-utils": {
        "copy_skin_weights": "Use normalize_skin_weights to clean up or mirror_skin_weights to flip.",
        "mirror_skin_weights": "Use normalize_skin_weights to clean up or copy_skin_weights to verify.",
        "normalize_skin_weights": "Use mirror_skin_weights or copy_skin_weights to complete the workflow.",
        "prune_skin_weights": "Use normalize_skin_weights to clean up or copy_skin_weights to propagate.",
    },
    "maya-spline-ik": {
        "add_stretch_to_spline_ik": "Use list_spline_ik_handles to review or set_spline_ik_twist to finalize.",
        "create_spline_ik": "Use set_spline_ik_twist to configure or add_stretch_to_spline_ik to rig.",
        "list_spline_ik_handles": "Use set_spline_ik_twist or add_stretch_to_spline_ik to manage.",
        "set_spline_ik_twist": "Use list_spline_ik_handles to verify or add_stretch_to_spline_ik to finish.",
    },
    "maya-texture-bake": {
        "bake_ambient_occlusion": "Use transfer_maps or bake_lighting to complete the baking workflow.",
        "bake_lighting": "Use bake_ambient_occlusion or transfer_maps to continue.",
        "list_bake_sets": "Use bake_lighting or bake_ambient_occlusion to run a bake.",
        "transfer_maps": "Use bake_lighting or bake_ambient_occlusion to complete the pipeline.",
    },
    "maya-toon": {
        "add_toon_outline": "Use set_outline_width to adjust or list_toon_outlines to review.",
        "create_toon_shader": "Use assign_material to apply or set_material_attribute to adjust the ramp.",
        "list_toon_outlines": "Use set_outline_width or delete to manage the listed outlines.",
        "set_outline_width": "Use list_toon_outlines to verify the change.",
    },
    "maya-utility": {
        "clean_scene": "Use check_scene_health in maya-scene-utils to verify remaining issues.",
        "create_utility_node": "Use connect_attributes to wire or list_node_connections to inspect.",
        "get_scene_statistics": "Use clean_scene to reduce node count or save_scene to archive.",
        "list_node_connections": "Use connect_attributes in maya-rig-utils or disconnect_nodes to manage.",
    },
    "maya-uv-ops": {
        "auto_unwrap": "Use layout_uvs to arrange the shells or export_uv_snapshot to inspect.",
        "copy_uvs": "Use layout_uvs to arrange or export_uv_snapshot to preview.",
        "export_uv_snapshot": "Use auto_unwrap or layout_uvs to adjust before exporting again.",
        "layout_uvs": "Use export_uv_snapshot to preview or bake_lighting in maya-texture-bake.",
        "normalize_uvs": "Use layout_uvs or export_uv_snapshot to verify.",
        "planar_mapping": "Use layout_uvs or export_uv_snapshot to check the result.",
        "set_uv_tile_workspace": "Use auto_unwrap or layout_uvs to use the UDIM workflow.",
        "transfer_uvs": "Use export_uv_snapshot to verify or bake_lighting to apply.",
        "unfold_uvs": "Use export_uv_snapshot to preview or layout_uvs to arrange.",
    },
    "maya-vertex-color": {
        "apply_vertex_color": "Use list_vertex_color_sets to verify or bake_lighting to export.",
        "bake_occlusion_to_vertex_color": "Use apply_vertex_color or list_vertex_color_sets to review.",
        "create_vertex_color_set": "Use apply_vertex_color to paint or list_vertex_color_sets to review.",
        "delete_vertex_color_set": "Use list_vertex_color_sets to confirm deletion.",
        "list_vertex_color_sets": "Use apply_vertex_color or delete_vertex_color_set to manage.",
    },
    "maya-xform-utils": {
        "bake_transforms": "Use freeze_transforms or reset_pivot to finalise the hierarchy.",
        "freeze_transforms": "Use reset_pivot to centre the pivot or match_transforms to snap objects.",
        "match_transforms": "Use freeze_transforms to lock in the new position.",
        "reset_pivot": "Use freeze_transforms or match_transforms to complete the workflow.",
    },
    "maya-xgen": {
        "attach_xgen_archive": "Use list_xgen_collections to verify or set_xgen_attribute to adjust.",
        "create_xgen_collection": "Use attach_xgen_archive or set_xgen_attribute to populate.",
        "list_xgen_collections": "Use set_xgen_attribute or attach_xgen_archive to manage.",
        "render_xgen_preview": "Use set_xgen_attribute to adjust density before a full render.",
        "set_xgen_attribute": "Use list_xgen_collections to verify or render_xgen_preview to preview.",
    },
}


def _get_prompt(skill_dir: str, script_stem: str) -> str:
    """Look up the prompt or generate a default."""
    skill_map = PROMPT_MAP.get(skill_dir, {})
    if script_stem in skill_map:
        return skill_map[script_stem]
    # Generic fallback
    action = script_stem.replace("_", " ")
    return "Check the result with list_{} or use related actions to continue.".format(
        skill_dir.replace("maya-", "").replace("-", "_")
    )


# ---------------------------------------------------------------------------
# Patch logic
# ---------------------------------------------------------------------------
# Pattern: maya_success(  <first-arg>,   ...  )  — without existing prompt=
# We want to insert  ,\n        prompt="..."  after the first argument.
#
# Strategy: match the whole call, check no "prompt=" inside, then rebuild.
# We use a simple state machine rather than regex to handle nested parens.

def _find_maya_success_calls(src: str):
    """Yield (start, end) spans of each maya_success(...) call in src."""
    pat = re.compile(r'\bmaya_success\s*\(')
    for m in pat.finditer(src):
        depth = 0
        idx = m.end() - 1  # position of opening '('
        while idx < len(src):
            c = src[idx]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    yield m.start(), idx + 1
                    break
            idx += 1


def patch_file(path: str, skill_dir: str, script_stem: str) -> bool:
    """Add prompt= to maya_success calls that are missing it. Return True if changed."""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()

    prompt_text = _get_prompt(skill_dir, script_stem)

    spans = list(_find_maya_success_calls(src))
    if not spans:
        return False

    changed = False
    # Process spans in reverse so offsets stay valid
    result = src
    for start, end in reversed(spans):
        call_src = result[start:end]
        if "prompt=" in call_src:
            continue  # already has prompt
        # Find position after the first argument (before any trailing comma or close paren)
        # Insert   ,\n        prompt="<text>"   after the first positional arg
        inner_start = call_src.index("(") + 1
        inner = call_src[inner_start:-1]

        # Determine indentation from the start of the call's line
        line_start = result.rfind("\n", 0, start) + 1
        base_indent = " " * (start - line_start)
        arg_indent = base_indent + "    "

        # Build the replacement: add prompt= after existing args
        inner_stripped = inner.rstrip()
        if inner_stripped.endswith(","):
            new_inner = "{}\n{}prompt=\"{}\",\n{}".format(
                inner_stripped, arg_indent, prompt_text, base_indent
            )
        else:
            new_inner = "{},\n{}prompt=\"{}\",\n{}".format(
                inner_stripped, arg_indent, prompt_text, base_indent
            )
        new_call = "maya_success(\n{}{}{}{}".format(
            arg_indent,
            inner_stripped.lstrip(),
            "",
            "",
        )
        # Simpler: just insert the prompt= keyword before the closing paren
        # keeping original whitespace
        insertion = ',\n{}prompt="{}"'.format(arg_indent, prompt_text)
        # Find last non-whitespace before closing paren
        end_inner = len(call_src) - 1  # index of ')'
        ws_start = end_inner
        while ws_start > 0 and call_src[ws_start - 1] in " \t\n\r,":
            ws_start -= 1
        trailing = call_src[ws_start:end_inner]
        # Remove trailing commas from trailing whitespace portion
        trailing_clean = re.sub(r",\s*$", "", trailing)
        new_call = call_src[:ws_start] + insertion + "\n" + base_indent + ")"
        result = result[:start] + new_call + result[end:]
        changed = True

    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(result)
    return changed


def main():
    patched = 0
    skipped = 0
    for skill_dir in sorted(os.listdir(SKILL_ROOT)):
        scripts_dir = os.path.join(SKILL_ROOT, skill_dir, "scripts")
        if not os.path.isdir(scripts_dir):
            continue
        for fname in sorted(os.listdir(scripts_dir)):
            if not fname.endswith(".py"):
                continue
            stem = fname[:-3]
            path = os.path.join(scripts_dir, fname)
            if patch_file(path, skill_dir, stem):
                patched += 1
                print("patched:", path)
            else:
                skipped += 1

    print("\nDone. Patched: {}, Already OK / no changes: {}".format(patched, skipped))


if __name__ == "__main__":
    main()
