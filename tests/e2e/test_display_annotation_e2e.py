"""E2E tests for maya-display and maya-annotation skills.

These tests are skipped automatically when ``maya.standalone`` is not
available (i.e., outside a mayapy / tahv/mayapy Docker environment).

Run locally::

    mayapy -m pytest tests/e2e/test_display_annotation_e2e.py -v

CI::

    docker run --rm -v $(pwd):/workspace -w /workspace \\
        tahv/mayapy:2025 \\
        mayapy -m pytest tests/e2e/test_display_annotation_e2e.py -v
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path

# Import third-party modules
import pytest

pytestmark = pytest.mark.e2e

SKILLS_ROOT = Path(__file__).parent.parent.parent / "src" / "dcc_mcp_maya" / "skills"


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
# maya-display E2E
# ---------------------------------------------------------------------------


class TestDisplayLayerE2E:
    """E2E tests for maya-display skill using real Maya standalone."""

    def test_create_display_layer_default(self):
        """Create a display layer with default name."""
        mod = _import_script("maya-display", "create_display_layer")
        result = mod.create_display_layer()

        assert result["success"] is True
        layer_name = result["context"]["layer_name"]
        assert layer_name

        # cleanup
        import maya.cmds as cmds

        if cmds.objExists(layer_name) and layer_name != "defaultLayer":
            cmds.delete(layer_name)

    def test_create_display_layer_with_name(self):
        """Create a named display layer."""
        mod = _import_script("maya-display", "create_display_layer")
        result = mod.create_display_layer(name="e2e_test_layer")

        assert result["success"] is True
        assert result["context"]["layer_name"] == "e2e_test_layer"

        import maya.cmds as cmds

        assert cmds.objExists("e2e_test_layer")
        assert cmds.objectType("e2e_test_layer") == "displayLayer"
        cmds.delete("e2e_test_layer")

    def test_create_display_layer_hidden(self):
        """Create a hidden display layer."""
        mod = _import_script("maya-display", "create_display_layer")
        result = mod.create_display_layer(name="e2e_hidden_layer", visibility=False)

        assert result["success"] is True

        import maya.cmds as cmds

        assert cmds.objExists("e2e_hidden_layer")
        vis = cmds.getAttr("e2e_hidden_layer.visibility")
        assert vis == 0
        cmds.delete("e2e_hidden_layer")

    def test_list_display_layers_has_default(self):
        """list_display_layers always includes defaultLayer."""
        mod = _import_script("maya-display", "list_display_layers")
        result = mod.list_display_layers()

        assert result["success"] is True
        names = [l["name"] for l in result["context"]["layers"]]
        assert "defaultLayer" in names

    def test_delete_default_layer_rejected(self):
        """Deleting defaultLayer is forbidden."""
        mod = _import_script("maya-display", "delete_display_layer")
        result = mod.delete_display_layer("defaultLayer")

        assert result["success"] is False

    def test_create_and_delete_layer(self):
        """Create then delete a display layer."""
        create_mod = _import_script("maya-display", "create_display_layer")
        delete_mod = _import_script("maya-display", "delete_display_layer")

        r_create = create_mod.create_display_layer(name="e2e_del_layer")
        assert r_create["success"] is True

        r_delete = delete_mod.delete_display_layer("e2e_del_layer")
        assert r_delete["success"] is True

        import maya.cmds as cmds

        assert not cmds.objExists("e2e_del_layer")

    def test_create_layer_with_object_and_set_layer(self):
        """Create a sphere, add it to a display layer, verify membership."""
        import maya.cmds as cmds

        sphere = cmds.polySphere(name="e2e_sphere_layer")[0]

        create_mod = _import_script("maya-display", "create_display_layer")
        r = create_mod.create_display_layer(name="e2e_obj_layer", objects=[sphere])

        assert r["success"] is True
        assert sphere in r["context"]["objects_added"]

        cmds.delete("e2e_obj_layer")
        cmds.delete(sphere)


# ---------------------------------------------------------------------------
# maya-annotation E2E
# ---------------------------------------------------------------------------


class TestAnnotationE2E:
    """E2E tests for maya-annotation skill using real Maya standalone."""

    def test_create_annotation_world_position(self):
        """Create annotation at a world position."""
        mod = _import_script("maya-annotation", "create_annotation")
        result = mod.create_annotation("E2E Test Note", position=[0.0, 2.0, 0.0])

        assert result["success"] is True
        ann_node = result["context"]["annotation_node"]
        transform_node = result["context"]["transform_node"]

        import maya.cmds as cmds

        assert cmds.objExists(ann_node)
        assert cmds.objectType(ann_node) == "annotationShape"
        assert cmds.objExists(transform_node)
        cmds.delete(transform_node)

    def test_create_annotation_attached_to_object(self):
        """Create annotation attached to a Maya object."""
        import maya.cmds as cmds

        sphere = cmds.polySphere(name="e2e_ann_sphere")[0]
        mod = _import_script("maya-annotation", "create_annotation")
        result = mod.create_annotation("Sphere Note", target_object=sphere)

        assert result["success"] is True
        cmds.delete(sphere)  # deleting parent also deletes annotation

    def test_list_annotations(self):
        """list_annotations returns correct count."""
        import maya.cmds as cmds

        create_mod = _import_script("maya-annotation", "create_annotation")
        list_mod = _import_script("maya-annotation", "list_annotations")

        # Create 2 annotations
        r1 = create_mod.create_annotation("Note A")
        r2 = create_mod.create_annotation("Note B")
        assert r1["success"] and r2["success"]

        r_list = list_mod.list_annotations()
        assert r_list["success"] is True
        texts = [a["text"] for a in r_list["context"]["annotations"]]
        assert "Note A" in texts
        assert "Note B" in texts

        cmds.delete(r1["context"]["transform_node"])
        cmds.delete(r2["context"]["transform_node"])

    def test_update_annotation_text(self):
        """Update annotation text in real Maya."""
        import maya.cmds as cmds

        create_mod = _import_script("maya-annotation", "create_annotation")
        update_mod = _import_script("maya-annotation", "update_annotation")

        r_create = create_mod.create_annotation("Original")
        assert r_create["success"] is True
        ann_node = r_create["context"]["annotation_node"]
        transform = r_create["context"]["transform_node"]

        r_update = update_mod.update_annotation(ann_node, text="Updated")
        assert r_update["success"] is True
        assert r_update["context"]["text"] == "Updated"

        # Verify in Maya
        assert cmds.getAttr("{}.text".format(ann_node)) == "Updated"
        cmds.delete(transform)

    def test_delete_annotation(self):
        """Delete annotation from scene."""
        import maya.cmds as cmds

        create_mod = _import_script("maya-annotation", "create_annotation")
        delete_mod = _import_script("maya-annotation", "delete_annotation")

        r_create = create_mod.create_annotation("To Delete")
        ann_node = r_create["context"]["annotation_node"]
        transform = r_create["context"]["transform_node"]

        r_delete = delete_mod.delete_annotation(ann_node)
        assert r_delete["success"] is True
        assert not cmds.objExists(transform)
