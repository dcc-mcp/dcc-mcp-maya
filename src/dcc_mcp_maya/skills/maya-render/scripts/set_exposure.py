"""Set typed Arnold exposure on one camera or light with native readback."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SUPPORTED_NODE_TYPES = frozenset(
    {
        "camera",
        "directionalLight",
        "pointLight",
        "spotLight",
        "areaLight",
        "aiAreaLight",
        "aiMeshLight",
        "aiPhotometricLight",
        "aiSkyDomeLight",
    }
)
_MIN_EXPOSURE = -20.0
_MAX_EXPOSURE = 20.0


def _resolve_target(cmds, target: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    node_type = str(cmds.nodeType(target))
    if node_type in _SUPPORTED_NODE_TYPES:
        return target, node_type, []

    shapes = list(cmds.listRelatives(target, shapes=True, fullPath=False) or [])
    matches = []
    for shape in shapes:
        shape_type = str(cmds.nodeType(shape))
        if shape_type in _SUPPORTED_NODE_TYPES:
            matches.append((str(shape), shape_type))
    if len(matches) == 1:
        return matches[0][0], matches[0][1], shapes
    return None, None, shapes


def set_exposure(target: str, exposure: float) -> dict:
    """Set one bounded Arnold exposure value and verify native scene state."""

    cmds = None
    attr = None
    previous = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not isinstance(target, str) or not target.strip() or len(target) > 512:
            return skill_error("Invalid exposure target", "target must be a non-empty Maya node name")
        if isinstance(exposure, bool) or not isinstance(exposure, (int, float)):
            return skill_error("Invalid exposure", "exposure must be a finite number")
        requested = float(exposure)
        if not math.isfinite(requested) or not _MIN_EXPOSURE <= requested <= _MAX_EXPOSURE:
            return skill_error(
                "Exposure is outside the supported range",
                "exposure must be finite and between {} and {} stops".format(_MIN_EXPOSURE, _MAX_EXPOSURE),
            )
        if not cmds.objExists(target):
            return skill_error("Exposure target was not found", "No Maya node exists with that name", target=target)

        node, node_type, shapes = _resolve_target(cmds, target)
        if not node:
            return skill_error(
                "Exposure target is ambiguous or unsupported",
                "target must resolve to exactly one supported camera or light shape",
                target=target,
                shapes=shapes,
                supported_node_types=sorted(_SUPPORTED_NODE_TYPES),
            )
        if not cmds.attributeQuery("aiExposure", node=node, exists=True):
            return skill_error(
                "Arnold exposure is unavailable on the target",
                "Load MtoA and choose a camera or light shape that exposes aiExposure.",
                target=target,
                node=node,
                node_type=node_type,
            )

        attr = "{}.aiExposure".format(node)
        previous = cmds.getAttr(attr)
        if isinstance(previous, bool) or not isinstance(previous, (int, float)):
            return skill_error(
                "Previous exposure readback was not numeric",
                "Maya returned an invalid aiExposure value before the write.",
                target=target,
                node=node,
                actual=previous,
            )
        cmds.setAttr(attr, requested)
        actual = cmds.getAttr(attr)
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            cmds.setAttr(attr, previous)
            return skill_error(
                "Exposure readback was not numeric",
                "Maya returned an invalid aiExposure value after the write.",
                target=target,
                node=node,
                actual=actual,
            )
        actual_value = float(actual)
        if not math.isfinite(actual_value) or abs(actual_value - requested) > 1e-6:
            cmds.setAttr(attr, previous)
            return skill_error(
                "Exposure write did not round-trip",
                "Native aiExposure readback differs from the requested value.",
                target=target,
                node=node,
                requested_exposure=requested,
                actual_exposure=actual_value,
            )

        return skill_success(
            "Set Arnold exposure on '{}' to {} stops".format(target, actual_value),
            target=target,
            node=node,
            node_type=node_type,
            previous_exposure=previous,
            exposure=actual_value,
            verified=True,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        if cmds is not None and attr is not None and previous is not None:
            try:
                cmds.setAttr(attr, previous)
            except Exception:
                pass
        return skill_exception(exc, message="Failed to set Arnold exposure")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point for typed Arnold exposure control."""

    return set_exposure(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
