"""Maya polygon mesh operation actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def get_poly_count(object_name: Optional[str] = None) -> dict:
    """Query polygon statistics for an object or the entire scene.

    Args:
        object_name: Transform or mesh shape name.  If None, queries the full
            scene.

    Returns:
        ToolResult dict with ``context.faces``, ``context.vertices``,
        ``context.edges``, and ``context.triangles``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if object_name:
            err = validate_node_exists(cmds, object_name)
            if err:
                return err
            targets = [object_name]
        else:
            targets = cmds.ls(type="mesh") or []

        total_faces = 0
        total_verts = 0
        total_edges = 0
        total_tris = 0
        per_object = []

        for target in targets:
            try:
                faces = cmds.polyEvaluate(target, face=True)
                verts = cmds.polyEvaluate(target, vertex=True)
                edges = cmds.polyEvaluate(target, edge=True)
                tris = cmds.polyEvaluate(target, triangle=True)
            except Exception:
                faces = verts = edges = tris = 0

            total_faces += faces if isinstance(faces, int) else 0
            total_verts += verts if isinstance(verts, int) else 0
            total_edges += edges if isinstance(edges, int) else 0
            total_tris += tris if isinstance(tris, int) else 0

            if object_name:
                per_object.append(
                    {
                        "name": target,
                        "faces": faces,
                        "vertices": verts,
                        "edges": edges,
                        "triangles": tris,
                    }
                )

        label = "Poly count for '{}'".format(object_name) if object_name else "Scene poly count"
        result_kwargs = {
            "faces": total_faces,
            "vertices": total_verts,
            "edges": total_edges,
            "triangles": total_tris,
        }
        if object_name:
            result_kwargs["objects"] = per_object

        return skill_success(
            label, **result_kwargs, prompt="Check the result with list_scripting or use related actions to continue."
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get poly count")


def apply_subdivision(
    object_name: str,
    level: int = 1,
    method: str = "preview",
) -> dict:
    """Apply subdivision to a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        level: Subdivision level / divisions.  Default: 1.
        method: ``"preview"`` (displaySmoothMesh — non-destructive) or
            ``"subdivide"`` (polySubdivideFacet — destructive).
            Default: ``"preview"``.

    Returns:
        ToolResult dict.
    """

    if method not in ("preview", "subdivide"):
        return skill_error(
            "Invalid method: {}".format(method),
            "Use 'preview' or 'subdivide'",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        shapes = cmds.listRelatives(object_name, shapes=True, type="mesh") or []
        if not shapes:
            if cmds.objectType(object_name) == "mesh":
                shapes = [object_name]
            else:
                return skill_error("'{}' has no polygon mesh shape".format(object_name))

        shape = shapes[0]

        if method == "preview":
            cmds.setAttr("{}.displaySmoothMesh".format(shape), 2)
            cmds.setAttr("{}.smoothLevel".format(shape), level)
        else:
            cmds.polySubdivideFacet(object_name, dv=level)

        return skill_success(
            "Subdivision applied to '{}' (method={}, level={})".format(object_name, method, level),
            object_name=object_name,
            method=method,
            level=level,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to apply subdivision")


def merge_vertices(
    object_name: str,
    threshold: float = 0.001,
) -> dict:
    """Merge coincident vertices on a polygon mesh.

    Args:
        object_name: Transform or mesh name.
        threshold: Distance threshold for merging.  Default: 0.001.

    Returns:
        ToolResult dict with ``context.merged_count`` (approximate).
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        before = cmds.polyEvaluate(object_name, vertex=True)
        cmds.polyMergeVertex(object_name, distance=threshold, ch=False)
        after = cmds.polyEvaluate(object_name, vertex=True)

        before_count = before if isinstance(before, int) else 0
        after_count = after if isinstance(after, int) else 0
        merged = before_count - after_count

        return skill_success(
            "Merged {} vertices on '{}' (threshold={})".format(merged, object_name, threshold),
            object_name=object_name,
            merged_count=merged,
            vertex_count_before=before_count,
            vertex_count_after=after_count,
            threshold=threshold,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to merge vertices")


def triangulate(object_name: str) -> dict:
    """Triangulate all faces of a polygon mesh.

    Args:
        object_name: Transform or mesh name.

    Returns:
        ToolResult dict with face counts before and after.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        before = cmds.polyEvaluate(object_name, face=True)
        cmds.polyTriangulate(object_name)
        after = cmds.polyEvaluate(object_name, face=True)

        before_count = before if isinstance(before, int) else 0
        after_count = after if isinstance(after, int) else 0

        return skill_success(
            "Triangulated '{}': {} -> {} faces".format(object_name, before_count, after_count),
            object_name=object_name,
            face_count_before=before_count,
            face_count_after=after_count,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to triangulate")


def cleanup_mesh(
    object_name: str,
    non_manifold: bool = True,
    lamina_faces: bool = True,
    invalid_components: bool = True,
) -> dict:
    """Clean up mesh issues such as non-manifold geometry and lamina faces.

    Args:
        object_name: Transform or mesh name.
        non_manifold: Fix non-manifold geometry.  Default: True.
        lamina_faces: Remove lamina (zero-area) faces.  Default: True.
        invalid_components: Remove invalid (degenerate) polygons.
            Default: True.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        kwargs = {
            "selectOnly": False,
            "nonManifold": 1 if non_manifold else 0,
            "lamina": 1 if lamina_faces else 0,
            "nsi": 1 if invalid_components else 0,
        }
        cmds.polyClean(object_name, **kwargs)

        return skill_success(
            "Cleaned mesh '{}'".format(object_name),
            object_name=object_name,
            non_manifold=non_manifold,
            lamina_faces=lamina_faces,
            invalid_components=invalid_components,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to clean mesh")


def get_mesh_edge_info(
    object_name: str,
    edge_indices: Optional[List[int]] = None,
) -> dict:
    """Query edge length and connected vertex indices for a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        edge_indices: Optional list of zero-based edge indices to query.
            If None, all edges are queried (may be slow on dense meshes).

    Returns:
        ToolResult dict with ``context.edges`` (list of dicts with
        ``index``, ``length``, ``vertices``), ``context.edge_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        total_edges = cmds.polyEvaluate(object_name, edge=True)
        if not isinstance(total_edges, int) or total_edges == 0:
            return skill_error("'{}' has no edges — ensure it is a polygon mesh".format(object_name))

        if edge_indices is None:
            indices = list(range(total_edges))
        else:
            invalid = [i for i in edge_indices if not (0 <= i < total_edges)]
            if invalid:
                return skill_error(
                    "Invalid edge indices: {}".format(invalid),
                    "Valid range is 0 to {}".format(total_edges - 1),
                )
            indices = list(edge_indices)

        edges = []
        for idx in indices:
            edge_comp = "{}.e[{}]".format(object_name, idx)
            # Edge length via polyInfo
            try:
                info_lines = cmds.polyInfo(edge_comp, edgeToVertex=True) or []
                verts = []
                for line in info_lines:
                    parts = line.strip().split()
                    # Format: EDGE n : v1 v2
                    colon_pos = [i for i, p in enumerate(parts) if p == ":"]
                    if colon_pos:
                        for p in parts[colon_pos[0] + 1 :]:
                            try:
                                verts.append(int(p))
                            except ValueError:
                                pass
            except Exception:
                verts = []

            try:
                # Edge length via arclen approximation
                length = None
                if verts and len(verts) >= 2:
                    v0_pos = cmds.pointPosition("{}.vtx[{}]".format(object_name, verts[0]), world=True)
                    v1_pos = cmds.pointPosition("{}.vtx[{}]".format(object_name, verts[1]), world=True)
                    length = (
                        (v1_pos[0] - v0_pos[0]) ** 2 + (v1_pos[1] - v0_pos[1]) ** 2 + (v1_pos[2] - v0_pos[2]) ** 2
                    ) ** 0.5
                    length = round(length, 6)
            except Exception:
                length = None

            edges.append({"index": idx, "length": length, "vertices": verts})

        return skill_success(
            "Edge info for '{}' ({} edge(s) queried)".format(object_name, len(edges)),
            object_name=object_name,
            edges=edges,
            edge_count=len(edges),
            total_edges=total_edges,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get edge info")


def select_by_material(material_name: str) -> dict:
    """Select all objects in the scene that use a given material.

    Looks up the shading group(s) associated with *material_name*, then
    queries the group members to find polygon mesh transforms.

    Args:
        material_name: Name of the material (shader) node, e.g.
            ``"lambert1"``, ``"blinn1"``, ``"aiStandardSurface1"``.

    Returns:
        ToolResult dict with ``context.objects`` (list of selected
        object names), ``context.count``, ``context.material``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, material_name)
        if err:
            return err

        # Find all shading engines connected to this material
        shading_engines = (
            cmds.listConnections(material_name, type="shadingEngine", source=False, destination=True) or []
        )

        if not shading_engines:
            return skill_success(
                "Material '{}' is not assigned to any objects".format(material_name),
                objects=[],
                count=0,
                material=material_name,
                prompt="Check the result with list_scripting or use related actions to continue.",
            )

        # Collect all mesh members from shading groups
        objects = []
        seen = set()
        for sg in shading_engines:
            members = cmds.sets(sg, query=True) or []
            for member in members:
                # member can be a transform or a component (face assignment)
                node = member.split(".")[0] if "." in member else member
                if node in seen:
                    continue
                seen.add(node)
                # Resolve to transform
                node_type = cmds.objectType(node)
                if node_type == "mesh":
                    parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
                    transform = parents[0] if parents else node
                elif node_type == "transform":
                    transform = node
                else:
                    continue
                if transform not in objects:
                    objects.append(transform)

        if objects:
            cmds.select(objects, replace=True)

        return skill_success(
            "Selected {} object(s) with material '{}'".format(len(objects), material_name),
            objects=objects,
            count=len(objects),
            material=material_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to select by material")


def create_proxy_mesh(
    object_name: str,
    reduction: float = 0.5,
    name: Optional[str] = None,
) -> dict:
    """Create a simplified proxy mesh from a polygon object.

    Uses ``cmds.polyReduce`` to produce a lower-resolution version of the
    source mesh.  The original object is left unchanged; a copy is created
    first and the reduction is applied to the copy.

    Args:
        object_name: Name of the source polygon mesh transform.
        reduction: Fraction of faces to *remove* (0.0 = no reduction,
            0.9 = remove 90% of faces).  Must be in range [0.0, 1.0).
            Default: 0.5.
        name: Optional name for the proxy mesh transform.  If None,
            Maya auto-generates a name.

    Returns:
        ToolResult dict with ``context.proxy_mesh``,
        ``context.original``, ``context.reduction``,
        ``context.face_count_before``, ``context.face_count_after``.
    """

    if not (0.0 <= reduction < 1.0):
        return skill_error(
            "Invalid reduction: {}".format(reduction),
            "reduction must be in range [0.0, 1.0)",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        shapes = cmds.listRelatives(object_name, shapes=True, type="mesh") or []
        if not shapes:
            obj_type = cmds.objectType(object_name)
            if obj_type != "mesh":
                return skill_error("'{}' has no polygon mesh shape".format(object_name))

        # Record original face count
        face_count_before = cmds.polyEvaluate(object_name, face=True)
        face_count_before = face_count_before if isinstance(face_count_before, int) else 0

        # Duplicate source mesh
        dup_kwargs = {}
        if name:
            dup_kwargs["name"] = name
        dup_result = cmds.duplicate(object_name, **dup_kwargs)
        proxy = dup_result[0] if dup_result else None
        if not proxy:
            return skill_error("Failed to duplicate '{}'".format(object_name))

        # Apply polyReduce
        percentage = (1.0 - reduction) * 100.0
        cmds.polyReduce(
            proxy,
            percentage=percentage,
            triangulate=False,
            constructionHistory=False,
        )

        face_count_after = cmds.polyEvaluate(proxy, face=True)
        face_count_after = face_count_after if isinstance(face_count_after, int) else 0

        return skill_success(
            "Created proxy mesh '{}' from '{}' (reduction={})".format(proxy, object_name, reduction),
            proxy_mesh=proxy,
            original=object_name,
            reduction=reduction,
            face_count_before=face_count_before,
            face_count_after=face_count_after,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create proxy mesh from '{}'".format(object_name))


def combine_meshes(
    objects,  # type: List[str]
    name=None,  # type: Optional[str]
):
    # type: (...) -> dict
    """Combine multiple polygon meshes into a single mesh.

    Uses ``cmds.polyUnite`` to merge the meshes and then deletes the original
    transform nodes.

    Args:
        objects: List of two or more polygon mesh transform names.
        name: Optional name for the resulting combined mesh.

    Returns:
        ToolResult dict with ``context.combined_mesh`` (name of the
        result) and ``context.input_count``.
    """

    if not objects or len(objects) < 2:
        return skill_error(
            "At least two objects are required for combine_meshes",
            "Provide a list of two or more polygon mesh names",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for obj in objects:
            err = validate_node_exists(cmds, obj)
            if err:
                return err

        kwargs = {}
        if name:
            kwargs["name"] = name
        result = cmds.polyUnite(*objects, constructionHistory=False, **kwargs) or []
        combined = result[0] if result else None
        if not combined:
            return skill_error(
                "polyUnite returned no result",
                "polyUnite did not produce any output mesh",
            )

        return skill_success(
            "Combined {} meshes into '{}'".format(len(objects), combined),
            combined_mesh=combined,
            input_count=len(objects),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to combine meshes")


def separate_mesh(
    object_name,  # type: str
):
    # type: (...) -> dict
    """Separate a polygon mesh that contains disconnected shells into individual meshes.

    Uses ``cmds.polySeparate`` to split each disconnected shell into its own
    transform node.

    Args:
        object_name: Name of the polygon mesh transform to separate.

    Returns:
        ToolResult dict with ``context.separated_meshes`` (list of
        result transform names) and ``context.count``.
    """

    if not object_name:
        return skill_error(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        result = cmds.polySeparate(object_name, constructionHistory=False) or []
        # polySeparate returns shape nodes; get their parent transforms
        separated = []
        for node in result:
            if cmds.objectType(node) == "transform":
                separated.append(node)
            else:
                parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
                if parents:
                    separated.append(parents[0])

        # Deduplicate while preserving order
        seen = set()  # type: set
        unique = []
        for s in separated:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return skill_success(
            "Separated '{}' into {} meshes".format(object_name, len(unique)),
            separated_meshes=unique,
            count=len(unique),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to separate mesh '{}'".format(object_name))


def extract_faces(
    object_name,  # type: str
    face_indices,  # type: List[int]
    keep_original=False,  # type: bool
    separate=True,  # type: bool
):
    # type: (...) -> dict
    """Extract (separate) specified polygon faces into a new mesh.

    Uses ``cmds.polyChipOff`` with *duplicate=keep_original* and then
    ``cmds.polySeparate`` if *separate* is True.

    Args:
        object_name: Polygon mesh transform name.
        face_indices: List of face indices to extract.
        keep_original: If ``True``, keep extracted faces on the original mesh
            (duplicate mode).  Default ``False`` (chip-off).
        separate: If ``True`` (default), separate the result into an
            independent mesh.

    Returns:
        ToolResult dict with ``context.extracted_mesh`` and
        ``context.face_count``.
    """

    if not object_name:
        return skill_error(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        )
    if not face_indices:
        return skill_error(
            "face_indices is required",
            "Provide a non-empty list of integer face indices",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        face_components = ["{}.f[{}]".format(object_name, idx) for idx in face_indices]

        cmds.polyChipOff(*face_components, constructionHistory=False, duplicate=keep_original, keepFacesTogether=True)

        extracted = object_name
        if separate:
            sep_result = cmds.polySeparate(object_name, constructionHistory=False) or []
            if sep_result:
                last = sep_result[-1]
                if cmds.objectType(last) == "transform":
                    extracted = last
                else:
                    parents = cmds.listRelatives(last, parent=True, fullPath=False) or []
                    extracted = parents[0] if parents else object_name

        return skill_success(
            "Extracted {} face(s) from '{}'".format(len(face_indices), object_name),
            extracted_mesh=extracted,
            face_count=len(face_indices),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to extract faces from '{}'".format(object_name))


def mirror_mesh(
    object_name,  # type: str
    axis="x",  # type: str
    cut_position=0.0,  # type: float
    merge_threshold=0.001,  # type: float
    merge_border=True,  # type: bool
):
    # type: (...) -> dict
    """Mirror a polygon mesh along a world axis and merge the result.

    Uses ``cmds.polyMirrorFace`` to mirror the mesh about a world-axis cut
    plane and optionally merge border vertices.

    Args:
        object_name: Polygon mesh transform name.
        axis: World axis to mirror across — ``"x"``, ``"y"``, or ``"z"``.
            Default ``"x"``.
        cut_position: World-space position of the mirror plane along *axis*.
            Default ``0.0``.
        merge_threshold: Distance threshold for merging border vertices.
            Default ``0.001``.
        merge_border: If ``True`` (default), merge vertices on the mirror
            border after mirroring.

    Returns:
        ToolResult dict with ``context.object_name``, ``context.axis``,
        ``context.cut_position``.
    """

    axis_lower = (axis or "x").lower()
    if axis_lower not in ("x", "y", "z"):
        return skill_error(
            "Invalid axis: {}".format(axis),
            "axis must be one of 'x', 'y', 'z'",
        )

    if not object_name:
        return skill_error(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        )

    # polyMirrorFace axis indices: 0=X, 1=Y, 2=Z
    axis_index = {"x": 0, "y": 1, "z": 2}[axis_lower]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        cmds.polyMirrorFace(
            object_name,
            constructionHistory=False,
            axis=axis_index,
            axisDirection=1,
            cutMesh=1,
            worldSpace=True,
            axisPos=cut_position,
            mergeMode=1 if merge_border else 0,
            mergeThresholdType=1,
            mergeThreshold=merge_threshold,
        )

        return skill_success(
            "Mirrored '{}' along {} axis at {}".format(object_name, axis_lower, cut_position),
            object_name=object_name,
            axis=axis_lower,
            cut_position=cut_position,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to mirror mesh '{}'".format(object_name))
