"""Extract (separate) specified polygon faces into a new mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not object_name:
        return error_result(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        ).to_dict()
    if not face_indices:
        return error_result(
            "face_indices is required",
            "Provide a non-empty list of integer face indices",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

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

        return success_result(
            "Extracted {} face(s) from '{}'".format(len(face_indices), object_name),
            extracted_mesh=extracted,
            face_count=len(face_indices),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("extract_faces failed")
        return error_result("Failed to extract faces from '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return extract_faces(**kwargs)


if __name__ == "__main__":
    import json

    result = extract_faces()
    print(json.dumps(result))
