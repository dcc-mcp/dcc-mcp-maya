"""Import animation curves from a file and optionally apply them to an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def import_animation_curves(
    file_path: str,
    target_object: Optional[str] = None,
    merge: bool = True,
) -> dict:
    """Import animation curves from a file and optionally apply them to an object.

    Args:
        file_path: Path to the ``.ma`` / ``.mb`` / ``.anim`` file to import.
        target_object: Name of the object to re-target the curves onto.
            If ``None``, curves are imported as-is without re-targeting.
        merge: When ``True``, existing keys on the target are merged rather
            than replaced (``cmds.file(i=True, mergeNamespacesOnClash=True)``).

    Returns:
        ActionResultModel dict with ``context.file_path`` and
        ``context.target_object``.
    """
    try:
        import os  # noqa: PLC0415

        import maya.cmds as cmds  # noqa: PLC0415

        if not os.path.isfile(file_path):
            return maya_error(
                "File not found: {}".format(file_path),
                "Cannot import animation curves: path does not exist",
            )

        import_kwargs = {
            "i": True,
            "ignoreVersion": True,
            "mergeNamespacesOnClash": merge,
            "force": True,
        }  # type: Dict

        cmds.file(file_path, **import_kwargs)

        if target_object and cmds.objExists(target_object):
            # Copy newly imported animCurves to target by name-matching
            # (best-effort; full re-targeting requires Maya's retarget API)
            imported_curves = cmds.ls(type="animCurve") or []
            for curve in imported_curves:
                connections = cmds.listConnections(curve, destination=True, plugs=True) or []
                for conn in connections:
                    attr = conn.split(".")[-1] if "." in conn else None
                    if attr and cmds.objExists("{}.{}".format(target_object, attr)):
                        try:
                            cmds.connectAttr(
                                "{}.output".format(curve),
                                "{}.{}".format(target_object, attr),
                                force=True,
                            )
                        except Exception:
                            pass

        return maya_success(
            "Imported animation curves from '{}'".format(file_path),
            file_path=file_path,
            target_object=target_object,
            merge=merge,
            prompt="Use list_animation_curves to verify the imported curves.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to import animation curves from '{}'".format(file_path))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`import_animation_curves`."""
    return import_animation_curves(**kwargs)


if __name__ == "__main__":
    import json

    result = import_animation_curves()
    print(json.dumps(result))
