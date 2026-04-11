"""Extract (separate) specified polygon faces into a new mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
        ActionResultModel dict with ``context.extracted_mesh`` and
        ``context.face_count``.
    """
    if not object_name:
        return maya_error(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        )
    if not face_indices:
        return maya_error(
            "face_indices is required",
            "Provide a non-empty list of integer face indices",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

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

        return maya_success(
            "Extracted {} face(s) from '{}'".format(len(face_indices), object_name),
            extracted_mesh=extracted,
            face_count=len(face_indices),
            prompt="Use combine_meshes or cleanup_mesh to post-process.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to extract faces from '{}'".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`extract_faces`."""
    return extract_faces(**kwargs)


if __name__ == "__main__":
    import json

    result = extract_faces()
    print(json.dumps(result))
