"""Stable typed result models for editable guide-curve tools."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class GuideCurveResult:
    """Machine-readable result for a created guide curve."""

    transform: str
    shape: str
    degree: int
    cv_count: int
    cluster_id: str
    display_color_rgb: List[float]
    root_to_tip: bool
    root_position: List[float]
    tip_position: List[float]
    arc_length: float
    cluster_median_arc_length: float
    length_deviation_ratio: float
    root_projection_distance: Optional[float]
    scalp_mesh: Optional[str]
    source_view: Optional[str]
    dominant_clump: Optional[str]


__all__ = ["GuideCurveResult"]
