"""E2E tests for maya-grooming and maya-paint-effects skills.

.. note::
    These skills have been removed from the source tree.  The tests are
    retained but skipped automatically until the skills are re-added.

These tests are skipped automatically when ``maya.standalone`` is not
available (i.e., outside a mayapy / tahv/mayapy Docker environment).

Render-dependent operations (playblast, GPU rendering) are skipped in
headless mode using the ``-k "not render"`` marker.

Run locally::

    mayapy -m pytest tests/e2e/test_grooming_painteffects_e2e.py -v

CI::

    docker run --rm -v $(pwd):/workspace -w /workspace \\
        tahv/mayapy:2025 \\
        mayapy -m pytest tests/e2e/test_grooming_painteffects_e2e.py -v -k "not render"
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from pathlib import Path

# Import third-party modules
import pytest

pytestmark = pytest.mark.e2e

SKILLS_ROOT = Path(__file__).parent.parent.parent / "src" / "dcc_mcp_maya" / "skills"

# Skip entire module when the referenced skill directories no longer exist.
_MISSING_SKILLS = [
    d for d in ("maya-grooming", "maya-paint-effects")
    if not (SKILLS_ROOT / d).is_dir()
]
if _MISSING_SKILLS:
    pytest.skip(
        "Skill directories not found: {} — skip phantom e2e".format(
            ", ".join(_MISSING_SKILLS)
        ),
        allow_module_level=True,
    )


def _import_script(skill_dir: str, script_name: str):
    """Import a skill script using importlib from the skills directory."""
    import importlib.util

    path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "e2e_{}_{}".format(skill_dir.replace("-", "_"), script_name),
        str(path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# maya-grooming E2E
# ---------------------------------------------------------------------------


class TestGroomingE2E:
    """E2E tests for maya-grooming skill using real Maya standalone."""

    def test_list_hair_systems_empty(self):
        """list_hair_systems on empty scene returns empty list."""
        mod = _import_script("maya-grooming", "list_hair_systems")
        result = mod.list_hair_systems()

        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["hair_systems"] == []

    def test_set_nhair_attribute_not_found(self):
        """set_nhair_attribute on nonexistent node returns error."""
        mod = _import_script("maya-grooming", "set_nhair_attribute")
        result = mod.set_nhair_attribute(hair_system="nonexistent_hair", attribute="stiffness", value=0.5)

        assert result["success"] is False

    @pytest.mark.parametrize(
        "attr,value",
        [
            ("stiffness", 0.8),
            ("clumpWidth", 0.2),
            ("clumpWidthScale", 1.0),
        ],
    )
    def test_set_nhair_attribute_invalid_node(self, attr, value):
        """set_nhair_attribute with invalid node returns error for any attribute."""
        mod = _import_script("maya-grooming", "set_nhair_attribute")
        result = mod.set_nhair_attribute(hair_system="ghost_hair", attribute=attr, value=value)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-paint-effects E2E
# ---------------------------------------------------------------------------


class TestPaintEffectsE2E:
    """E2E tests for maya-paint-effects skill using real Maya standalone."""

    def test_list_strokes_empty(self):
        """list_strokes on empty scene returns empty list."""
        mod = _import_script("maya-paint-effects", "list_strokes")
        result = mod.list_strokes()

        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["strokes"] == []

    def test_delete_stroke_not_found(self):
        """delete_stroke on nonexistent node returns error."""
        mod = _import_script("maya-paint-effects", "delete_stroke")
        result = mod.delete_stroke(stroke="nonexistent_stroke")

        assert result["success"] is False

    def test_delete_all_strokes_empty_scene(self):
        """delete_stroke with delete_all=True on empty scene is safe."""
        mod = _import_script("maya-paint-effects", "delete_stroke")
        result = mod.delete_stroke(delete_all=True)

        # Should succeed (nothing to delete)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_delete_stroke_no_args(self):
        """delete_stroke with no args returns error (neither stroke nor delete_all given)."""
        mod = _import_script("maya-paint-effects", "delete_stroke")
        result = mod.delete_stroke()

        assert result["success"] is False

    def test_list_and_delete_round_trip(self):
        """After list returns empty, delete_stroke delete_all=True is idempotent."""
        list_mod = _import_script("maya-paint-effects", "list_strokes")
        delete_mod = _import_script("maya-paint-effects", "delete_stroke")

        r_list = list_mod.list_strokes()
        initial_count = r_list["context"]["count"]

        r_delete = delete_mod.delete_stroke(delete_all=True)
        assert r_delete["success"] is True
        assert r_delete["context"]["count"] == initial_count
