"""Round 35 — deep edge-case tests for maya-toon and maya-constraints-advanced.

Covers positive-guard patterns (cmds.objExists used for logic, not error returns)
and comprehensive branch coverage for all 8 scripts.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call, load_and_call_with_mel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cmds(**attrs):
    """Return a MagicMock with preset attributes."""
    m = MagicMock()
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


def _call(rel_path, mock_cmds, **kwargs):
    return load_and_call(rel_path, mock_cmds, func_name="main", **kwargs)


def _call_with_mel(rel_path, mock_cmds, **kwargs):
    return load_and_call_with_mel(rel_path, mock_cmds, func_name="main", **kwargs)


# ===========================================================================
# maya-toon / add_toon_outline
# ===========================================================================


class TestAddToonOutline:
    """Deep tests for add_toon_outline.py.

    add_toon_outline imports both maya.cmds and maya.mel inside the function
    body, so we use _call_with_mel to ensure both are mocked.
    """

    _SCRIPT = "maya-toon/scripts/add_toon_outline.py"

    def _cmds(self, **kw):
        m = MagicMock()
        # Defaults that make happy path work
        m.objectType.return_value = "transform"
        m.listRelatives.return_value = ["pSphereShape1"]
        m.ls.side_effect = lambda *a, **kw2: (["pfxToon1"] if kw2.get("type") == "pfxToon" else [])
        m.rename.return_value = "pfxToon1"
        m.attributeQuery.return_value = True
        for k, v in kw.items():
            setattr(m, k, v)
        return m

    def test_no_objects_no_selection(self):
        """Returns error when no objects given and selection is empty."""
        m = self._cmds()
        m.ls.side_effect = lambda *a, **kw: []  # empty selection
        result = _call_with_mel(self._SCRIPT, m, objects=None)
        assert result["success"] is False
        assert "no objects" in result["message"].lower()

    def test_no_mesh_shapes_found(self):
        """Returns error when objects have no mesh children."""
        m = self._cmds()
        m.objectType.return_value = "transform"
        m.listRelatives.return_value = []  # no mesh shapes
        result = _call_with_mel(self._SCRIPT, m, objects=["locator1"])
        assert result["success"] is False
        assert "no mesh shapes" in result["message"].lower()

    def test_direct_mesh_shape_input(self):
        """Accepts direct mesh shape nodes without listRelatives lookup."""
        m = self._cmds()
        m.objectType.return_value = "mesh"  # input is already a mesh shape
        result = _call_with_mel(self._SCRIPT, m, objects=["pSphereShape1"])
        assert result["success"] is True
        assert result["context"]["toon_node"] == "pfxToon1"

    def test_happy_path_transform_input(self):
        """Transform object → resolved mesh shape → pfxToon created."""
        m = self._cmds()
        result = _call_with_mel(self._SCRIPT, m, objects=["pSphere1"])
        assert result["success"] is True
        assert "pfxToon" in result["context"]["toon_node"]
        assert len(result["context"]["meshes"]) >= 1

    def test_custom_name_applied(self):
        """Custom name is applied via cmds.rename."""
        m = self._cmds()
        m.rename.return_value = "myToon"
        result = _call_with_mel(self._SCRIPT, m, objects=["pSphere1"], name="myToon")
        assert result["success"] is True
        assert result["context"]["toon_node"] == "myToon"

    def test_rename_exception_does_not_fail(self):
        """If rename raises, the original node name is used without error."""
        m = self._cmds()
        m.rename.side_effect = RuntimeError("name clash")
        # last toon node is "pfxToon1", name arg differs → triggers rename
        result = _call_with_mel(self._SCRIPT, m, objects=["pSphere1"], name="myToon")
        # Should still succeed despite rename failure
        assert result["success"] is True

    def test_line_color_applied(self):
        """Custom line_color is applied to lineColorR/G/B attributes."""
        m = self._cmds()
        result = _call_with_mel(
            self._SCRIPT, m,
            objects=["pSphere1"],
            line_color=[1.0, 0.0, 0.0],
        )
        assert result["success"] is True
        # setAttr called for lineWidth + 3 color channels
        assert m.setAttr.call_count >= 4

    def test_default_black_color_used(self):
        """When line_color is None, default black [0,0,0] is applied."""
        m = self._cmds()
        result = _call_with_mel(self._SCRIPT, m, objects=["pSphere1"], line_color=None)
        assert result["success"] is True

    def test_prompt_present(self):
        """prompt key must be non-empty in success result."""
        m = self._cmds()
        result = _call_with_mel(self._SCRIPT, m, objects=["pSphere1"])
        assert result.get("prompt")

    def test_attributequery_false_skips_setattr(self):
        """If attributeQuery returns False, setAttr is NOT called for that attr."""
        m = self._cmds()
        m.attributeQuery.return_value = False  # no attributes exist
        result = _call_with_mel(self._SCRIPT, m, objects=["pSphere1"])
        assert result["success"] is True
        m.setAttr.assert_not_called()

    def test_uses_selection_when_objects_none(self):
        """When objects=None, selection is obtained via cmds.ls(selection=True)."""
        m = self._cmds()
        # Override ls: selection returns ["pSphere1"], pfxToon returns ["pfxToon1"]
        def _ls_side(*a, **kw):
            if kw.get("selection"):
                return ["pSphere1"]
            if kw.get("type") == "pfxToon":
                return ["pfxToon1"]
            return []
        m.ls.side_effect = _ls_side
        result = _call_with_mel(self._SCRIPT, m, objects=None)
        assert result["success"] is True


# ===========================================================================
# maya-toon / create_toon_shader
# ===========================================================================


class TestCreateToonShader:
    """Deep tests for create_toon_shader.py."""

    _SCRIPT = "maya-toon/scripts/create_toon_shader.py"

    def _cmds(self, **kw):
        m = MagicMock()
        m.shadingNode.return_value = "toonShader1"
        m.sets.return_value = "toonShader1_SG"
        m.objExists.return_value = True
        for k, v in kw.items():
            setattr(m, k, v)
        return m

    def test_happy_path_defaults(self):
        result = _call(self._SCRIPT, self._cmds())
        assert result["success"] is True
        assert result["context"]["shader"] == "toonShader1"
        assert result["context"]["shading_group"] == "toonShader1_SG"

    def test_custom_name(self):
        m = self._cmds()
        m.shadingNode.return_value = "celShader"
        m.sets.return_value = "celShader_SG"
        result = _call(self._SCRIPT, m, name="celShader")
        assert result["context"]["shader"] == "celShader"

    def test_color_ramp_applied(self):
        """Custom 3-element color_ramp causes 12 setAttr calls (4 per band)."""
        m = self._cmds()
        result = _call(
            self._SCRIPT, m,
            color_ramp=[[0.1, 0.1, 0.1], [0.5, 0.5, 0.5], [0.9, 0.9, 0.9]],
        )
        assert result["success"] is True
        # Each band: colorR, colorG, colorB, position = 4 calls × 3 bands = 12
        assert m.setAttr.call_count == 12

    def test_invalid_color_ramp_uses_default(self):
        """color_ramp with wrong length falls back to default ramp."""
        m = self._cmds()
        result = _call(self._SCRIPT, m, color_ramp=[[1.0, 0.0, 0.0]])  # only 1 entry
        assert result["success"] is True
        # Default still causes 12 setAttr calls
        assert m.setAttr.call_count == 12

    def test_assign_to_existing_objects(self):
        """assign_to objects that exist are added to the shading group."""
        m = self._cmds()
        m.objExists.return_value = True
        result = _call(self._SCRIPT, m, assign_to=["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["assigned_to"] == ["pSphere1", "pCube1"]
        # cmds.sets called once for SG creation + twice for assignments
        assert m.sets.call_count >= 3

    def test_assign_to_nonexistent_objects_skipped(self):
        """assign_to objects that don't exist are silently skipped."""
        m = self._cmds()
        m.objExists.return_value = False  # nothing exists
        result = _call(self._SCRIPT, m, assign_to=["ghost1", "ghost2"])
        assert result["success"] is True
        assert result["context"]["assigned_to"] == []

    def test_setattr_exception_does_not_fail(self):
        """If ramp setAttr raises, the shader is still created."""
        m = self._cmds()
        m.setAttr.side_effect = RuntimeError("locked attr")
        result = _call(self._SCRIPT, m)
        assert result["success"] is True

    def test_prompt_present(self):
        result = _call(self._SCRIPT, self._cmds())
        assert result.get("prompt")


# ===========================================================================
# maya-toon / list_toon_outlines
# ===========================================================================


class TestListToonOutlines:
    """Deep tests for list_toon_outlines.py."""

    _SCRIPT = "maya-toon/scripts/list_toon_outlines.py"

    def test_empty_scene(self):
        m = MagicMock()
        m.ls.return_value = []
        result = _call(self._SCRIPT, m)
        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["outlines"] == []

    def test_two_toon_nodes(self):
        m = MagicMock()
        m.ls.return_value = ["pfxToon1", "pfxToon2"]
        m.getAttr.side_effect = lambda attr: 1.5 if "pfxToon1" in attr else 2.0
        m.listConnections.return_value = ["pSphereShape1"]
        result = _call(self._SCRIPT, m)
        assert result["success"] is True
        assert result["context"]["count"] == 2
        nodes = [o["node"] for o in result["context"]["outlines"]]
        assert "pfxToon1" in nodes

    def test_getattr_exception_sets_none(self):
        """If getAttr raises for a node, line_width is None (not a failure)."""
        m = MagicMock()
        m.ls.return_value = ["pfxToon1"]
        m.getAttr.side_effect = RuntimeError("bad attr")
        m.listConnections.return_value = []
        result = _call(self._SCRIPT, m)
        assert result["success"] is True
        assert result["context"]["outlines"][0]["line_width"] is None

    def test_listconnections_exception_sets_empty_meshes(self):
        m = MagicMock()
        m.ls.return_value = ["pfxToon1"]
        m.getAttr.return_value = 1.0
        m.listConnections.side_effect = RuntimeError("no connections")
        result = _call(self._SCRIPT, m)
        assert result["success"] is True
        assert result["context"]["outlines"][0]["meshes"] == []

    def test_prompt_present(self):
        m = MagicMock()
        m.ls.return_value = []
        result = _call(self._SCRIPT, m)
        assert result.get("prompt")


# ===========================================================================
# maya-toon / set_outline_width
# ===========================================================================


class TestSetOutlineWidth:
    """Deep tests for set_outline_width.py."""

    _SCRIPT = "maya-toon/scripts/set_outline_width.py"

    def _cmds(self, exists=True, obj_type="pfxToon", has_profile_attr=True):
        m = MagicMock()
        m.objExists.return_value = exists
        m.objectType.return_value = obj_type
        m.attributeQuery.return_value = has_profile_attr
        return m

    def test_missing_node_returns_error(self):
        m = self._cmds(exists=False)
        result = _call(self._SCRIPT, m, toon_node="pfxToon1", line_width=2.0)
        assert result["success"] is False

    def test_wrong_node_type_returns_error(self):
        m = self._cmds(obj_type="transform")
        result = _call(self._SCRIPT, m, toon_node="pSphere1", line_width=2.0)
        assert result["success"] is False
        assert "not a pfxtoon node" in result["message"].lower()

    def test_happy_path_no_profile(self):
        """profile_line_width=-1 → no profileLineWidth set."""
        m = self._cmds()
        result = _call(self._SCRIPT, m, toon_node="pfxToon1", line_width=2.0)
        assert result["success"] is True
        assert result["context"]["profile_line_width"] is None

    def test_happy_path_with_profile(self):
        """profile_line_width>=0 → profileLineWidth is set."""
        m = self._cmds()
        result = _call(self._SCRIPT, m, toon_node="pfxToon1", line_width=2.0, profile_line_width=1.5)
        assert result["success"] is True
        assert result["context"]["profile_line_width"] == 1.5
        # setAttr called for lineWidth + profileLineWidth
        assert m.setAttr.call_count == 2

    def test_profile_attr_absent_skips_setattr(self):
        """If attributeQuery returns False, profileLineWidth is not set."""
        m = self._cmds(has_profile_attr=False)
        result = _call(self._SCRIPT, m, toon_node="pfxToon1", line_width=1.0, profile_line_width=0.5)
        assert result["success"] is True
        assert result["context"]["profile_line_width"] is None
        # Only lineWidth setAttr
        assert m.setAttr.call_count == 1

    def test_context_keys(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, toon_node="pfxToon1", line_width=3.0)
        ctx = result["context"]
        assert ctx["toon_node"] == "pfxToon1"
        assert ctx["line_width"] == 3.0

    def test_prompt_present(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, toon_node="pfxToon1", line_width=1.0)
        assert result.get("prompt")


# ===========================================================================
# maya-constraints-advanced / add_pole_vector_constraint
# ===========================================================================


class TestAddPoleVectorConstraint:
    """Deep tests for add_pole_vector_constraint.py."""

    _SCRIPT = "maya-constraints-advanced/scripts/add_pole_vector_constraint.py"

    def _cmds(self, pole_exists=True, ik_exists=True, ik_type="ikHandle"):
        m = MagicMock()
        call_count = [0]

        def _obj_exists(name):
            call_count[0] += 1
            if name == "poleLocator":
                return pole_exists
            return ik_exists

        m.objExists.side_effect = _obj_exists
        m.objectType.return_value = ik_type
        m.poleVectorConstraint.return_value = ["poleVectorConstraint1"]
        return m

    def test_missing_pole_object(self):
        m = self._cmds(pole_exists=False)
        result = _call(self._SCRIPT, m, pole_object="poleLocator", ik_handle="ikHandle1")
        assert result["success"] is False

    def test_missing_ik_handle(self):
        m = self._cmds(ik_exists=False)
        result = _call(self._SCRIPT, m, pole_object="poleLocator", ik_handle="ikHandle1")
        assert result["success"] is False

    def test_wrong_node_type(self):
        m = self._cmds(ik_type="transform")
        result = _call(self._SCRIPT, m, pole_object="poleLocator", ik_handle="myJoint")
        assert result["success"] is False
        assert "not an ik handle" in result["message"].lower()

    def test_happy_path(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, pole_object="poleLocator", ik_handle="ikHandle1")
        assert result["success"] is True
        assert result["context"]["constraint_node"] == "poleVectorConstraint1"
        assert result["context"]["pole_object"] == "poleLocator"
        assert result["context"]["ik_handle"] == "ikHandle1"

    def test_custom_weight(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, pole_object="poleLocator", ik_handle="ikHandle1", weight=0.5)
        assert result["success"] is True
        m.poleVectorConstraint.assert_called_once()
        call_kwargs = m.poleVectorConstraint.call_args[1]
        assert call_kwargs.get("weight") == 0.5

    def test_empty_constraint_result(self):
        """If poleVectorConstraint returns empty list, constraint_node is ''."""
        m = self._cmds()
        m.poleVectorConstraint.return_value = []
        result = _call(self._SCRIPT, m, pole_object="poleLocator", ik_handle="ikHandle1")
        assert result["success"] is True
        assert result["context"]["constraint_node"] == ""

    def test_prompt_present(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, pole_object="poleLocator", ik_handle="ikHandle1")
        assert result.get("prompt")


# ===========================================================================
# maya-constraints-advanced / bake_constraint
# ===========================================================================


class TestBakeConstraint:
    """Deep tests for bake_constraint.py."""

    _SCRIPT = "maya-constraints-advanced/scripts/bake_constraint.py"

    def _cmds(self, obj_exists=True, start=1.0, end=24.0):
        m = MagicMock()
        m.objExists.return_value = obj_exists
        m.playbackOptions.side_effect = lambda *a, **kw: start if kw.get("minTime") else end
        m.listRelatives.return_value = []
        m.listConnections.return_value = []
        return m

    def test_missing_object(self):
        m = self._cmds(obj_exists=False)
        result = _call(self._SCRIPT, m, objects=["pSphere1"])
        assert result["success"] is False

    def test_happy_path_defaults(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, objects=["pSphere1"])
        assert result["success"] is True
        assert result["context"]["baked_objects"] == ["pSphere1"]
        assert result["context"]["frame_range"] == [1, 24]

    def test_custom_frame_range(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, objects=["pSphere1"], start_frame=10.0, end_frame=50.0)
        assert result["context"]["frame_range"] == [10, 50]
        # playbackOptions should NOT be called when explicit range provided
        m.playbackOptions.assert_not_called()

    def test_remove_constraints_true(self):
        """Constraints are deleted when remove_constraints=True (default)."""
        m = self._cmds()
        m.listRelatives.return_value = ["parentConstraint1"]
        m.listConnections.return_value = []
        m.objExists.side_effect = lambda n: True  # constraint node also exists
        result = _call(self._SCRIPT, m, objects=["pSphere1"], remove_constraints=True)
        assert result["success"] is True
        assert result["context"]["constraints_removed"] is True
        m.delete.assert_called()

    def test_remove_constraints_false(self):
        """Constraints are preserved when remove_constraints=False."""
        m = self._cmds()
        result = _call(self._SCRIPT, m, objects=["pSphere1"], remove_constraints=False)
        assert result["success"] is True
        m.delete.assert_not_called()

    def test_multiple_objects(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, objects=["pSphere1", "pCube1", "pPlane1"])
        assert result["success"] is True
        assert len(result["context"]["baked_objects"]) == 3

    def test_constraint_not_existing_skipped(self):
        """Constraints that don't exist at delete time are silently skipped."""
        m = self._cmds()
        m.listRelatives.return_value = ["parentConstraint1"]
        m.listConnections.return_value = []
        existing = {"pSphere1": True, "parentConstraint1": False}
        m.objExists.side_effect = lambda n: existing.get(n, True)
        result = _call(self._SCRIPT, m, objects=["pSphere1"], remove_constraints=True)
        assert result["success"] is True
        m.delete.assert_not_called()

    def test_prompt_present(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, objects=["pSphere1"])
        assert result.get("prompt")


# ===========================================================================
# maya-constraints-advanced / get_constraint_weights
# ===========================================================================


class TestGetConstraintWeights:
    """Deep tests for get_constraint_weights.py."""

    _SCRIPT = "maya-constraints-advanced/scripts/get_constraint_weights.py"

    def _cmds(self, exists=True, target_list=None, w_exists=True, w_val=1.0):
        m = MagicMock()
        m.objExists.return_value = exists
        m.objectType.return_value = "parentConstraint"
        m.listAttr.return_value = ["driver1W0", "driver2W1"]
        m.listConnections.return_value = target_list if target_list is not None else ["driver1", "driver2"]
        m.getAttr.return_value = w_val

        def _obj_exists(name):
            # constraint node itself
            if name == "parentConstraint1":
                return exists
            # weight attrs
            return w_exists

        m.objExists.side_effect = _obj_exists
        return m

    def test_missing_constraint(self):
        m = MagicMock()
        m.objExists.return_value = False
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1")
        assert result["success"] is False

    def test_no_drivers(self):
        m = self._cmds(target_list=[])
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1")
        assert result["success"] is True
        assert result["context"]["weights"] == []

    def test_two_drivers_happy_path(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1")
        assert result["success"] is True
        weights = result["context"]["weights"]
        assert len(weights) == 2
        assert weights[0]["driver"] == "driver1"

    def test_w_attr_fallback(self):
        """When primary w_attr doesn't exist, fallback via listAttr is used."""
        m = self._cmds(w_exists=False)
        # Primary attr doesn't exist → fallback to listAttr result
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1")
        assert result["success"] is True

    def test_getattr_exception_defaults_to_1(self):
        """If getAttr raises, weight defaults to 1.0."""
        m = self._cmds()
        m.getAttr.side_effect = RuntimeError("attr error")
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1")
        assert result["success"] is True
        for w in result["context"]["weights"]:
            assert w["weight"] == 1.0

    def test_constraint_type_returned(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1")
        assert result["context"]["constraint_type"] == "parentConstraint"

    def test_prompt_present(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1")
        assert result.get("prompt")


# ===========================================================================
# maya-constraints-advanced / set_constraint_weight
# ===========================================================================


class TestSetConstraintWeight:
    """Deep tests for set_constraint_weight.py."""

    _SCRIPT = "maya-constraints-advanced/scripts/set_constraint_weight.py"

    def _cmds(self, exists=True, attrs=None):
        m = MagicMock()
        m.objExists.return_value = exists
        m.listAttr.return_value = attrs if attrs is not None else ["driver1W0", "driver2W1"]
        return m

    def test_missing_node(self):
        m = self._cmds(exists=False)
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1", driver_index=0, weight=1.0)
        assert result["success"] is False

    def test_no_matching_weight_attr(self):
        """Returns error when no attribute ends with W<index>."""
        m = self._cmds(attrs=["someAttr", "otherAttr"])
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1", driver_index=0, weight=1.0)
        assert result["success"] is False
        assert "no weight attribute" in result["message"].lower()

    def test_happy_path_driver_0(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1", driver_index=0, weight=1.0)
        assert result["success"] is True
        assert result["context"]["driver_index"] == 0
        assert result["context"]["weight"] == 1.0
        assert result["context"]["constraint_node"] == "parentConstraint1"

    def test_happy_path_driver_1(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1", driver_index=1, weight=0.0)
        assert result["success"] is True
        assert result["context"]["weight"] == 0.0
        assert "driver2W1" in result["context"]["weight_attribute"]

    def test_setattr_called_with_correct_value(self):
        m = self._cmds()
        _call(self._SCRIPT, m, constraint_node="parentConstraint1", driver_index=0, weight=0.75)
        m.setAttr.assert_called_once_with("parentConstraint1.driver1W0", 0.75)

    def test_weight_attribute_in_context(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1", driver_index=0, weight=1.0)
        assert "weight_attribute" in result["context"]
        assert result["context"]["weight_attribute"].endswith("W0")

    def test_prompt_present(self):
        m = self._cmds()
        result = _call(self._SCRIPT, m, constraint_node="parentConstraint1", driver_index=0, weight=1.0)
        assert result.get("prompt")
