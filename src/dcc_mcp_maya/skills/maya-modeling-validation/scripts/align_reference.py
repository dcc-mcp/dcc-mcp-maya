"""Align a Maya model to a scene reference with bounded edits."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _bounds(cmds: Any, name: str) -> Optional[Dict[str, List[float]]]:
    values = cmds.exactWorldBoundingBox(name)
    if not isinstance(values, (list, tuple)) or len(values) < 6:
        return None
    return {"min": [float(value) for value in values[:3]], "max": [float(value) for value in values[3:6]]}


def _center(bounds: Dict[str, List[float]]) -> List[float]:
    return [(bounds["min"][index] + bounds["max"][index]) / 2.0 for index in range(3)]


def _diagonal(bounds: Dict[str, List[float]]) -> float:
    return math.sqrt(sum((bounds["max"][index] - bounds["min"][index]) ** 2 for index in range(3)))


def _distance(first: List[float], second: List[float]) -> float:
    return math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


def align_reference(
    object_name: str,
    reference_object: str,
    apply: bool = False,
    max_scale_ratio: float = 10.0,
    tolerance: float = 0.001,
) -> dict:
    """Propose or apply uniform scale and center alignment to a model."""
    try:
        max_ratio = float(max_scale_ratio)
        tolerance_value = float(tolerance)
    except (TypeError, ValueError):
        return skill_error("Invalid alignment bounds", "max_scale_ratio and tolerance must be numeric")
    if not math.isfinite(max_ratio) or not 1.0 < max_ratio <= 100.0:
        return skill_error("Invalid max_scale_ratio", "max_scale_ratio must be greater than 1 and no more than 100")
    if not math.isfinite(tolerance_value) or not 0.0 < tolerance_value <= 10.0:
        return skill_error("Invalid tolerance", "tolerance must be greater than 0 and no more than 10")
    if not isinstance(object_name, str) or not object_name or object_name == reference_object:
        return skill_error(
            "Invalid alignment objects", "object_name and reference_object must be different non-empty names"
        )
    transaction = None
    try:
        import maya.cmds as cmds

        for name in (object_name, reference_object):
            if not cmds.objExists(name):
                return skill_error(
                    "Alignment object not found", "Maya object does not exist: {}".format(name), object_name=name
                )
        source_before = _bounds(cmds, object_name)
        reference = _bounds(cmds, reference_object)
        if source_before is None or reference is None:
            return skill_error("Alignment bounds unavailable", "Maya did not return complete world bounds")
        source_diagonal = _diagonal(source_before)
        reference_diagonal = _diagonal(reference)
        if source_diagonal <= 0.0 or reference_diagonal <= 0.0:
            return skill_error("Degenerate alignment bounds", "Both objects must have non-zero world bounds")
        scale_ratio = reference_diagonal / source_diagonal
        if scale_ratio < 1.0 / max_ratio or scale_ratio > max_ratio:
            return skill_error(
                "Alignment scale outside bound",
                "The required uniform scale exceeds max_scale_ratio",
                scale_ratio=scale_ratio,
                max_scale_ratio=max_ratio,
            )
        translation = [_center(reference)[index] - _center(source_before)[index] * scale_ratio for index in range(3)]
        proposal = {
            "scale_ratio": scale_ratio,
            "translation": translation,
            "source_bounds_before": source_before,
            "reference_bounds": reference,
            "applied": False,
        }
        if not apply:
            return skill_success("Reference alignment proposal created", **proposal)

        from dcc_mcp_maya._mutation import MayaUndoChunk

        transaction = MayaUndoChunk(cmds, "dcc_mcp_align_reference")
        transaction.begin()
        cmds.scale(scale_ratio, scale_ratio, scale_ratio, object_name, relative=True, worldSpace=True)
        cmds.move(translation[0], translation[1], translation[2], object_name, relative=True, worldSpace=True)
        source_after = _bounds(cmds, object_name)
        if source_after is None:
            return skill_error(
                "Alignment readback unavailable",
                "Maya did not return post-alignment bounds",
                applied=True,
                **transaction.rollback(lambda: _bounds(cmds, object_name) == source_before),
            )
        center_error = _distance(_center(source_after), _center(reference))
        proposal.update(
            source_bounds_after=source_after,
            center_error=center_error,
            applied=True,
            within_tolerance=center_error <= tolerance_value,
        )
        if center_error > tolerance_value:
            return skill_error(
                "Reference alignment verification failed",
                "Aligned model center is outside the requested tolerance",
                **proposal,
                **transaction.rollback(lambda: _bounds(cmds, object_name) == source_before),
            )
        transaction.commit()
        return skill_success("Reference alignment applied and verified", **proposal)
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        receipt = {}
        if transaction is not None and getattr(transaction, "_open", False):
            receipt = transaction.rollback(lambda: _bounds(cmds, object_name) == source_before)
        return skill_exception(exc, message="Failed to align Maya model to reference", **receipt)


@skill_entry
def main(**kwargs) -> dict:
    return align_reference(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
