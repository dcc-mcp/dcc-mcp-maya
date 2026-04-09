"""Built-in Maya actions for the MCP server.

Progressive discovery & registration
--------------------------------------
Actions are loaded in two phases that mirror ``dcc-mcp-core``'s
``scan_and_load`` SOP:

1. **Discovery** — :func:`discover_action_modules` walks every ``*.py``
   module in this package and collects those that expose a ``_ACTIONS``
   list.  Import errors are caught and logged at WARNING level so a
   broken optional module never prevents the core set from loading.

2. **Registration** — :func:`register_all` iterates the discovered
   modules and registers each action with the ``ActionRegistry``.

This means adding a new action file is as simple as dropping a ``*.py``
module into this directory — no edits to ``__init__.py`` are required.

Action module contract
----------------------
Each module **must** expose a ``_ACTIONS`` list of
``(name, description, category, tags)`` tuples that describe the actions
it provides.  The callable itself must live at module scope under the
same ``name``.

Example::

    # src/dcc_mcp_maya/actions/my_module.py
    _ACTIONS = [
        ("my_action", "Does something useful", "utility", ["tag1"]),
    ]

    def my_action(**kwargs):
        ...
        return {"success": True, "message": "...", "context": {}}
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import logging
import pkgutil
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core module load order
# ---------------------------------------------------------------------------
# Core modules are loaded first (deterministic), then all others
# alphabetically.  This mirrors dcc-mcp-core's scan_and_load SOP where
# built-in actions take precedence over extended/optional ones.
_CORE_MODULES = [
    "scene",
    "primitives",
    "scripting",
]

# ---------------------------------------------------------------------------
# Public re-exports — kept for backward-compatibility with code that does
# ``from dcc_mcp_maya.actions import new_scene`` etc.
# ---------------------------------------------------------------------------

# ── core ──────────────────────────────────────────────────────────────────────
from dcc_mcp_maya.actions.primitives import (  # noqa: E402
    create_cube,
    create_cylinder,
    create_plane,
    create_sphere,
    delete_objects,
    get_transform,
    rename_object,
    set_transform,
)
from dcc_mcp_maya.actions.scene import (  # noqa: E402
    center_pivot,
    create_locator,
    duplicate_object,
    export_scene,
    freeze_transforms,
    get_bounding_box,
    get_scene_info,
    get_selection,
    get_session_info,
    group_objects,
    list_cameras,
    list_objects,
    lock_object,
    new_scene,
    open_scene,
    parent_object,
    save_scene,
    select_by_type,
    set_frame_rate,
    set_selection,
    set_visibility,
)
from dcc_mcp_maya.actions.scripting import execute_mel, execute_python  # noqa: E402

# ── extended — re-exported for ``from dcc_mcp_maya.actions import <name>`` ───
from dcc_mcp_maya.actions.animation import (  # noqa: E402
    bake_constraints,
    bake_simulation,
    delete_keyframes,
    export_animation_curves,
    get_current_time,
    get_keyframes,
    import_animation_curves,
    list_animation_curves,
    query_scene_time_info,
    set_animation_curve_tangent,
    set_current_time,
    set_keyframe,
    set_timeline,
)
from dcc_mcp_maya.actions.attributes import get_attribute, set_attribute  # noqa: E402
from dcc_mcp_maya.actions.cameras import (  # noqa: E402
    create_camera,
    get_camera_info,
    list_all_cameras,
    set_camera_attribute,
)
from dcc_mcp_maya.actions.constraints import (  # noqa: E402
    add_constraint,
    create_constraint_weighted,
    list_constraints,
    remove_constraint,
)
from dcc_mcp_maya.actions.deformer_advanced import (  # noqa: E402
    create_cluster,
    create_lattice,
    sculpt_deformer,
    set_cluster_weights,
    wire_deformer,
)
from dcc_mcp_maya.actions.display import (  # noqa: E402
    create_display_layer,
    delete_display_layer,
    list_display_layers,
    set_display_layer,
)
from dcc_mcp_maya.actions.dynamics import (  # noqa: E402
    connect_field_to_objects,
    create_dynamic_field,
    create_ncloth,
    create_nrigid,
    create_nucleus,
    list_ncloth_nodes,
    list_nrigid_nodes,
    set_ncloth_attribute,
    set_nrigid_attribute,
    set_nucleus_attribute,
)
from dcc_mcp_maya.actions.expressions import (  # noqa: E402
    create_expression,
    delete_expression,
    list_expressions,
)
from dcc_mcp_maya.actions.lighting import (  # noqa: E402
    create_light,
    delete_light,
    list_lights,
    set_light_attribute,
)
from dcc_mcp_maya.actions.materials import (  # noqa: E402
    assign_material,
    create_material,
    get_material_connections,
    get_shader_assignment,
    list_materials,
    list_shading_groups,
    reset_to_default_material,
    set_material_attribute,
)
from dcc_mcp_maya.actions.mesh_ops import (  # noqa: E402
    apply_subdivision,
    cleanup_mesh,
    combine_meshes,
    create_proxy_mesh,
    extract_faces,
    get_mesh_edge_info,
    get_poly_count,
    merge_vertices,
    mirror_mesh,
    select_by_material,
    separate_mesh,
    triangulate,
)
from dcc_mcp_maya.actions.namespaces import (  # noqa: E402
    delete_namespace,
    rename_namespace,
    set_namespace,
)
from dcc_mcp_maya.actions.node_attrs import (  # noqa: E402
    add_attribute,
    delete_attribute,
    list_attributes,
)
from dcc_mcp_maya.actions.node_graph import (  # noqa: E402
    apply_symmetry,
    connect_attr,
    delete_history,
    disconnect_attr,
    get_dag_path,
    list_connections,
    list_history,
    smooth_mesh,
    transfer_attributes,
)
from dcc_mcp_maya.actions.references import (  # noqa: E402
    create_reference,
    list_namespaces,
    list_references,
    reload_reference,
    remove_reference,
    unload_reference,
)
from dcc_mcp_maya.actions.render import (  # noqa: E402
    capture_viewport,
    export_selection,
    get_scene_render_stats,
    import_file,
    set_render_quality,
    set_render_settings,
)
from dcc_mcp_maya.actions.render_layers import (  # noqa: E402
    create_render_layer,
    delete_render_layer,
    list_render_layers,
    set_render_layer,
    set_render_layer_attribute,
)
from dcc_mcp_maya.actions.rigging import (  # noqa: E402
    assign_deformer,
    blend_shape_add_target,
    create_blend_shape,
    create_curve,
    create_ik_handle,
    create_joint,
    mirror_joints,
    set_driven_key,
    set_ik_fk_blend,
    set_joint_limit,
    set_joint_orient,
    skin_cluster_bind,
)
from dcc_mcp_maya.actions.scene_utils import (  # noqa: E402
    align_objects,
    create_annotation,
    set_object_color,
    set_pivot,
    set_shading_mode,
    toggle_gpu_override,
)
from dcc_mcp_maya.actions.sets import (  # noqa: E402
    add_to_set,
    create_set,
    list_sets,
    remove_from_set,
)
from dcc_mcp_maya.actions.texture_bake import (  # noqa: E402
    bake_textures,
    list_color_spaces,
    set_color_management,
)
from dcc_mcp_maya.actions.utility import create_utility_node, get_scene_statistics  # noqa: E402
from dcc_mcp_maya.actions.uv_ops import (  # noqa: E402
    copy_uvs,
    create_uv_set,
    delete_uv_set,
    get_uv_info,
    get_uv_shell_info,
    normalize_uvs,
    project_uvs,
    unfold_uvs,
)
from dcc_mcp_maya.actions.vertex_color import (  # noqa: E402
    create_color_set,
    get_vertex_color,
    remove_vertex_colors,
    set_vertex_color,
)

__all__ = [
    # ── scene (core) ──────────────────────────────────────────────────────────
    "new_scene",
    "save_scene",
    "open_scene",
    "list_objects",
    "get_selection",
    "set_selection",
    "get_session_info",
    "group_objects",
    "parent_object",
    "select_by_type",
    "duplicate_object",
    "freeze_transforms",
    "center_pivot",
    "get_bounding_box",
    "set_visibility",
    "lock_object",
    "get_scene_info",
    "export_scene",
    "set_frame_rate",
    "list_cameras",
    "create_locator",
    # ── primitives (core) ─────────────────────────────────────────────────────
    "create_sphere",
    "create_cube",
    "create_cylinder",
    "create_plane",
    "delete_objects",
    "set_transform",
    "get_transform",
    "rename_object",
    # ── scripting (core) ──────────────────────────────────────────────────────
    "execute_mel",
    "execute_python",
    # ── animation ─────────────────────────────────────────────────────────────
    "set_keyframe",
    "get_keyframes",
    "set_timeline",
    "get_current_time",
    "set_current_time",
    "delete_keyframes",
    "bake_simulation",
    "list_animation_curves",
    "set_animation_curve_tangent",
    "bake_constraints",
    "export_animation_curves",
    "import_animation_curves",
    "query_scene_time_info",
    # ── attributes ────────────────────────────────────────────────────────────
    "get_attribute",
    "set_attribute",
    # ── cameras ───────────────────────────────────────────────────────────────
    "create_camera",
    "set_camera_attribute",
    "get_camera_info",
    "list_all_cameras",
    # ── constraints ───────────────────────────────────────────────────────────
    "add_constraint",
    "remove_constraint",
    "list_constraints",
    "create_constraint_weighted",
    # ── deformer advanced ─────────────────────────────────────────────────────
    "create_cluster",
    "set_cluster_weights",
    "create_lattice",
    "wire_deformer",
    "sculpt_deformer",
    # ── display layers ────────────────────────────────────────────────────────
    "create_display_layer",
    "set_display_layer",
    "delete_display_layer",
    "list_display_layers",
    # ── dynamics ──────────────────────────────────────────────────────────────
    "create_nucleus",
    "set_nucleus_attribute",
    "create_dynamic_field",
    "connect_field_to_objects",
    "create_ncloth",
    "create_nrigid",
    "set_ncloth_attribute",
    "list_ncloth_nodes",
    "set_nrigid_attribute",
    "list_nrigid_nodes",
    # ── expressions ───────────────────────────────────────────────────────────
    "create_expression",
    "list_expressions",
    "delete_expression",
    # ── lighting ──────────────────────────────────────────────────────────────
    "create_light",
    "set_light_attribute",
    "list_lights",
    "delete_light",
    # ── materials ─────────────────────────────────────────────────────────────
    "create_material",
    "assign_material",
    "set_material_attribute",
    "list_materials",
    "get_shader_assignment",
    "reset_to_default_material",
    "get_material_connections",
    "list_shading_groups",
    # ── mesh ops ──────────────────────────────────────────────────────────────
    "get_poly_count",
    "apply_subdivision",
    "merge_vertices",
    "triangulate",
    "cleanup_mesh",
    "combine_meshes",
    "separate_mesh",
    "extract_faces",
    "mirror_mesh",
    "get_mesh_edge_info",
    "select_by_material",
    "create_proxy_mesh",
    # ── namespaces ────────────────────────────────────────────────────────────
    "set_namespace",
    "rename_namespace",
    "delete_namespace",
    # ── node attrs ────────────────────────────────────────────────────────────
    "add_attribute",
    "delete_attribute",
    "list_attributes",
    # ── node graph ────────────────────────────────────────────────────────────
    "connect_attr",
    "disconnect_attr",
    "list_connections",
    "get_dag_path",
    "smooth_mesh",
    "list_history",
    "delete_history",
    "apply_symmetry",
    "transfer_attributes",
    # ── references ────────────────────────────────────────────────────────────
    "create_reference",
    "list_references",
    "remove_reference",
    "reload_reference",
    "unload_reference",
    "list_namespaces",
    # ── render ────────────────────────────────────────────────────────────────
    "set_render_settings",
    "capture_viewport",
    "import_file",
    "export_selection",
    "set_render_quality",
    "get_scene_render_stats",
    # ── render layers ─────────────────────────────────────────────────────────
    "create_render_layer",
    "set_render_layer",
    "list_render_layers",
    "delete_render_layer",
    "set_render_layer_attribute",
    # ── rigging ───────────────────────────────────────────────────────────────
    "create_joint",
    "create_curve",
    "set_joint_orient",
    "mirror_joints",
    "create_ik_handle",
    "assign_deformer",
    "create_blend_shape",
    "skin_cluster_bind",
    "blend_shape_add_target",
    "set_driven_key",
    "set_ik_fk_blend",
    "set_joint_limit",
    # ── scene utils ───────────────────────────────────────────────────────────
    "set_pivot",
    "align_objects",
    "create_annotation",
    "set_object_color",
    "toggle_gpu_override",
    "set_shading_mode",
    # ── sets ──────────────────────────────────────────────────────────────────
    "create_set",
    "add_to_set",
    "remove_from_set",
    "list_sets",
    # ── texture bake ──────────────────────────────────────────────────────────
    "bake_textures",
    "set_color_management",
    "list_color_spaces",
    # ── utility ───────────────────────────────────────────────────────────────
    "create_utility_node",
    "get_scene_statistics",
    # ── uv ops ────────────────────────────────────────────────────────────────
    "get_uv_info",
    "create_uv_set",
    "delete_uv_set",
    "project_uvs",
    "copy_uvs",
    "get_uv_shell_info",
    "unfold_uvs",
    "normalize_uvs",
    # ── vertex color ──────────────────────────────────────────────────────────
    "set_vertex_color",
    "get_vertex_color",
    "create_color_set",
    "remove_vertex_colors",
    # ── discovery helpers ─────────────────────────────────────────────────────
    "discover_action_modules",
    "register_all",
]

# ---------------------------------------------------------------------------
# Phase 1: Discovery
# ---------------------------------------------------------------------------


def discover_action_modules() -> List[Tuple[str, List]]:
    """Discover all action modules in this package.

    Walks every importable ``*.py`` sub-module under ``dcc_mcp_maya.actions``
    and collects those that expose a ``_ACTIONS`` list.  Import errors are
    caught and logged at WARNING level so a broken optional module never
    prevents the core set from loading.

    Load order mirrors ``dcc-mcp-core`` SOP:

    * Core modules first (``scene``, ``primitives``, ``scripting``)
    * Remaining modules in alphabetical order

    Returns:
        A list of ``(module_name, _ACTIONS)`` pairs in stable order.
    """
    import dcc_mcp_maya.actions as _pkg  # noqa: PLC0415

    pkg_path = _pkg.__path__
    pkg_name = _pkg.__name__

    available: List[str] = []
    for _, mod_name, is_pkg in pkgutil.iter_modules(pkg_path):
        if not is_pkg and mod_name != "__init__":
            available.append(mod_name)

    # Stable order: core first, then the rest alphabetically
    core_set = set(_CORE_MODULES)
    ordered = _CORE_MODULES + sorted(m for m in available if m not in core_set)

    results: List[Tuple[str, List]] = []
    for mod_name in ordered:
        full_name = f"{pkg_name}.{mod_name}"
        try:
            mod = importlib.import_module(full_name)
        except Exception as exc:
            logger.warning("Skipping action module %s: %s", full_name, exc)
            continue

        actions = getattr(mod, "_ACTIONS", None)
        if actions is None:
            logger.debug("Module %s has no _ACTIONS list, skipping", full_name)
            continue

        results.append((mod_name, actions))
        logger.debug("Discovered %d action(s) in %s", len(actions), full_name)

    return results


# ---------------------------------------------------------------------------
# Phase 2: Registration
# ---------------------------------------------------------------------------


def register_all(registry) -> Dict[str, int]:
    """Discover and register all built-in Maya actions into *registry*.

    Uses :func:`discover_action_modules` to progressively find every action
    module, then registers each action with the ``ActionRegistry``.

    This mirrors the ``dcc-mcp-core`` ``scan_and_load`` SOP:

    1. Scan — find all modules with ``_ACTIONS``
    2. Load — import and register actions, skipping failures gracefully
    3. Report — return a summary dict for observability

    Args:
        registry: An ``ActionRegistry`` instance from ``dcc_mcp_core``.

    Returns:
        A summary dict ``{module_name: action_count}`` for observability.
    """
    summary: Dict[str, int] = {}
    discovered = discover_action_modules()

    for mod_name, actions in discovered:
        count = 0
        for entry in actions:
            name, description, category, tags = entry
            try:
                registry.register(
                    name,
                    description=description,
                    category=category,
                    tags=tags,
                    dcc="maya",
                    version="1.0.0",
                )
                count += 1
            except Exception as exc:
                logger.warning(
                    "Failed to register action %r from %s: %s",
                    name,
                    mod_name,
                    exc,
                )

        summary[mod_name] = count
        logger.debug(
            "Registered %d/%d action(s) from module %s",
            count,
            len(actions),
            mod_name,
        )

    total = sum(summary.values())
    logger.info(
        "Maya actions registered: %d total across %d modules",
        total,
        len(summary),
    )
    return summary
