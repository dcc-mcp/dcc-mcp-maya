"""Tests for Round 5 new actions: assign_deformer, create_blend_shape,
skin_cluster_bind, get_attribute, set_attribute.

All tests mock maya.cmds so no real Maya installation is required.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload():
    """Remove dcc_mcp_maya modules so fresh mocks are picked up."""
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]


def _no_maya():
    return patch.dict(sys.modules, {"maya": None, "maya.cmds": None})


@pytest.fixture()
def mock_maya():
    """Standard Maya mock with sane defaults for deformer / attribute tests."""
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.objectType.return_value = "transform"
    cmds_mock.cluster.return_value = ["clusterDeformer1", "cluster1Handle"]
    cmds_mock.lattice.return_value = ["ffd1Lattice", "ffd1Base", "ffd1"]
    cmds_mock.nonLinear.return_value = ["bend1", "bend1Handle"]
    cmds_mock.deformer.return_value = ["blendShape1"]
    cmds_mock.blendShape.return_value = ["blendShape1"]
    cmds_mock.skinCluster.return_value = ["skinCluster1"]
    cmds_mock.getAttr.return_value = 1.0
    cmds_mock.select.return_value = None

    with patch.dict(
        sys.modules,
        {
            "maya": MagicMock(cmds=cmds_mock, utils=MagicMock()),
            "maya.cmds": cmds_mock,
            "maya.utils": MagicMock(),
        },
    ):
        yield cmds_mock


# ===========================================================================
# assign_deformer
# ===========================================================================

class TestAssignDeformer:
    def test_cluster_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import assign_deformer
        result = assign_deformer("pSphere1")
        assert result["success"] is True
        assert result["context"]["deformer_type"] == "cluster"
        assert result["context"]["deformer_name"] == "clusterDeformer1"
        assert result["context"]["handle_name"] == "cluster1Handle"

    def test_lattice(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import assign_deformer
        mock_maya.lattice.return_value = ["ffd1", "ffd1Base", "ffd1Lattice"]
        result = assign_deformer("pCube1", deformer_type="lattice")
        assert result["success"] is True
        assert result["context"]["deformer_type"] == "lattice"

    def test_nonlinear_bend(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import assign_deformer
        result = assign_deformer("pSphere1", deformer_type="bend")
        assert result["success"] is True
        assert result["context"]["deformer_type"] == "bend"
        assert result["context"]["deformer_name"] == "bend1"

    def test_unsupported_type_returns_error(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import assign_deformer
        result = assign_deformer("pSphere1", deformer_type="unknownDeformer")
        assert result["success"] is False
        assert "Unsupported deformer type" in result["message"]

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        _reload()
        from dcc_mcp_maya.actions.rigging import assign_deformer
        result = assign_deformer("nonExistent", deformer_type="cluster")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_blend_shape_via_deformer(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import assign_deformer
        result = assign_deformer("pSphere1", deformer_type="blendShape")
        assert result["success"] is True
        assert result["context"]["deformer_name"] == "blendShape1"

    def test_no_maya_import_error(self):
        _reload()
        with _no_maya():
            _reload()
            from dcc_mcp_maya.actions.rigging import assign_deformer
            result = assign_deformer("pSphere1")
        assert result["success"] is False
        assert "Maya not available" in result["message"]

    def test_exception_returns_error(self, mock_maya):
        mock_maya.cluster.side_effect = RuntimeError("cluster exploded")
        _reload()
        from dcc_mcp_maya.actions.rigging import assign_deformer
        result = assign_deformer("pSphere1", deformer_type="cluster")
        assert result["success"] is False
        assert "cluster exploded" in result.get("error", "")


# ===========================================================================
# create_blend_shape
# ===========================================================================

class TestCreateBlendShape:
    def test_with_targets(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import create_blend_shape
        result = create_blend_shape(
            base_mesh="baseMesh",
            target_meshes=["targetA", "targetB"],
        )
        assert result["success"] is True
        assert result["context"]["blend_shape_name"] == "blendShape1"
        assert result["context"]["target_count"] == 2

    def test_no_targets(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import create_blend_shape
        result = create_blend_shape(base_mesh="baseMesh")
        assert result["success"] is True
        assert result["context"]["target_count"] == 0

    def test_with_custom_name(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import create_blend_shape
        mock_maya.blendShape.return_value = ["myBS"]
        result = create_blend_shape(base_mesh="baseMesh", name="myBS")
        assert result["success"] is True
        assert result["context"]["blend_shape_name"] == "myBS"

    def test_base_mesh_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        _reload()
        from dcc_mcp_maya.actions.rigging import create_blend_shape
        result = create_blend_shape(base_mesh="ghost")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_target_not_found(self, mock_maya):
        # base exists, targets don't
        mock_maya.objExists.side_effect = lambda n: n == "baseMesh"
        _reload()
        from dcc_mcp_maya.actions.rigging import create_blend_shape
        result = create_blend_shape(base_mesh="baseMesh", target_meshes=["ghostTarget"])
        assert result["success"] is False
        assert "Target meshes not found" in result["message"]

    def test_no_maya(self):
        _reload()
        with _no_maya():
            _reload()
            from dcc_mcp_maya.actions.rigging import create_blend_shape
            result = create_blend_shape(base_mesh="baseMesh")
        assert result["success"] is False

    def test_exception_propagated(self, mock_maya):
        mock_maya.blendShape.side_effect = RuntimeError("bad topology")
        _reload()
        from dcc_mcp_maya.actions.rigging import create_blend_shape
        result = create_blend_shape(base_mesh="baseMesh", target_meshes=["targetA"])
        assert result["success"] is False
        assert "bad topology" in result.get("error", "")


# ===========================================================================
# skin_cluster_bind
# ===========================================================================

class TestSkinClusterBind:
    def test_basic_bind(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import skin_cluster_bind
        result = skin_cluster_bind(
            joints=["joint1", "joint2"],
            mesh="pSphere1",
        )
        assert result["success"] is True
        assert result["context"]["skin_cluster_name"] == "skinCluster1"
        assert result["context"]["joint_count"] == 2

    def test_custom_name(self, mock_maya):
        _reload()
        mock_maya.skinCluster.return_value = ["mySkin"]
        from dcc_mcp_maya.actions.rigging import skin_cluster_bind
        result = skin_cluster_bind(joints=["joint1"], mesh="pSphere1", name="mySkin")
        assert result["success"] is True
        assert result["context"]["skin_cluster_name"] == "mySkin"

    def test_empty_joints_returns_error(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import skin_cluster_bind
        result = skin_cluster_bind(joints=[], mesh="pSphere1")
        assert result["success"] is False
        assert "No joints" in result["message"]

    def test_mesh_not_found(self, mock_maya):
        # joints exist, mesh doesn't
        mock_maya.objExists.side_effect = lambda n: n.startswith("joint")
        _reload()
        from dcc_mcp_maya.actions.rigging import skin_cluster_bind
        result = skin_cluster_bind(joints=["joint1"], mesh="ghostMesh")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_joint_not_found(self, mock_maya):
        # mesh exists, joint doesn't
        mock_maya.objExists.side_effect = lambda n: n == "pSphere1"
        _reload()
        from dcc_mcp_maya.actions.rigging import skin_cluster_bind
        result = skin_cluster_bind(joints=["ghostJoint"], mesh="pSphere1")
        assert result["success"] is False
        assert "Joints not found" in result["message"]

    def test_no_maya(self):
        _reload()
        with _no_maya():
            _reload()
            from dcc_mcp_maya.actions.rigging import skin_cluster_bind
            result = skin_cluster_bind(joints=["joint1"], mesh="pSphere1")
        assert result["success"] is False

    def test_max_influences_passed_through(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import skin_cluster_bind
        result = skin_cluster_bind(
            joints=["j1", "j2", "j3"],
            mesh="mesh",
            max_influences=2,
        )
        assert result["success"] is True
        assert result["context"]["max_influences"] == 2

    def test_exception_propagated(self, mock_maya):
        mock_maya.skinCluster.side_effect = RuntimeError("skin failed")
        _reload()
        from dcc_mcp_maya.actions.rigging import skin_cluster_bind
        result = skin_cluster_bind(joints=["j1"], mesh="pSphere1")
        assert result["success"] is False
        assert "skin failed" in result.get("error", "")


# ===========================================================================
# get_attribute
# ===========================================================================

class TestGetAttribute:
    def test_scalar_attribute(self, mock_maya):
        mock_maya.getAttr.return_value = 5.0
        _reload()
        from dcc_mcp_maya.actions.attributes import get_attribute
        result = get_attribute("pSphere1", "translateX")
        assert result["success"] is True
        assert result["context"]["value"] == 5.0
        assert result["context"]["attribute"] == "translateX"

    def test_compound_attribute_flattened(self, mock_maya):
        mock_maya.getAttr.return_value = [(1.0, 2.0, 3.0)]
        _reload()
        from dcc_mcp_maya.actions.attributes import get_attribute
        result = get_attribute("pSphere1", "translate")
        assert result["success"] is True
        assert result["context"]["value"] == [1.0, 2.0, 3.0]

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        _reload()
        from dcc_mcp_maya.actions.attributes import get_attribute
        result = get_attribute("ghost", "tx")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_attribute_not_found(self, mock_maya):
        # node exists, attribute doesn't
        mock_maya.objExists.side_effect = lambda n: n == "pSphere1"
        _reload()
        from dcc_mcp_maya.actions.attributes import get_attribute
        result = get_attribute("pSphere1", "fakeAttr")
        assert result["success"] is False
        assert "Attribute not found" in result["message"]

    def test_no_maya(self):
        _reload()
        with _no_maya():
            _reload()
            from dcc_mcp_maya.actions.attributes import get_attribute
            result = get_attribute("pSphere1", "tx")
        assert result["success"] is False

    def test_exception_propagated(self, mock_maya):
        mock_maya.getAttr.side_effect = RuntimeError("locked")
        _reload()
        from dcc_mcp_maya.actions.attributes import get_attribute
        result = get_attribute("pSphere1", "tx")
        assert result["success"] is False
        assert "locked" in result.get("error", "")

    def test_boolean_value(self, mock_maya):
        mock_maya.getAttr.return_value = True
        _reload()
        from dcc_mcp_maya.actions.attributes import get_attribute
        result = get_attribute("pSphere1", "visibility")
        assert result["success"] is True
        assert result["context"]["value"] is True


# ===========================================================================
# set_attribute
# ===========================================================================

class TestSetAttribute:
    def test_set_scalar(self, mock_maya):
        mock_maya.getAttr.return_value = False  # not locked
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("pSphere1", "translateX", 10.0)
        assert result["success"] is True
        assert result["context"]["value"] == 10.0

    def test_set_vector(self, mock_maya):
        mock_maya.getAttr.return_value = False
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("pSphere1", "translate", [1.0, 2.0, 3.0])
        assert result["success"] is True
        assert result["context"]["value"] == [1.0, 2.0, 3.0]

    def test_set_string(self, mock_maya):
        mock_maya.getAttr.return_value = False
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("pSphere1", "notes", "hello")
        assert result["success"] is True
        assert result["context"]["value"] == "hello"

    def test_locked_attr_no_force(self, mock_maya):
        mock_maya.getAttr.return_value = True  # locked
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("pSphere1", "tx", 5.0, force=False)
        assert result["success"] is False
        assert "locked" in result["message"]

    def test_locked_attr_with_force(self, mock_maya):
        mock_maya.getAttr.return_value = True  # locked
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("pSphere1", "tx", 5.0, force=True)
        assert result["success"] is True

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("ghost", "tx", 1.0)
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_attribute_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n == "pSphere1"
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("pSphere1", "fakeAttr", 1.0)
        assert result["success"] is False
        assert "Attribute not found" in result["message"]

    def test_no_maya(self):
        _reload()
        with _no_maya():
            _reload()
            from dcc_mcp_maya.actions.attributes import set_attribute
            result = set_attribute("pSphere1", "tx", 1.0)
        assert result["success"] is False

    def test_exception_propagated(self, mock_maya):
        mock_maya.getAttr.return_value = False
        mock_maya.setAttr.side_effect = RuntimeError("read only")
        _reload()
        from dcc_mcp_maya.actions.attributes import set_attribute
        result = set_attribute("pSphere1", "tx", 1.0)
        assert result["success"] is False
        assert "read only" in result.get("error", "")


# ===========================================================================
# register_all — total action count
# ===========================================================================

class TestRegisterAllRound5:
    def test_total_action_count(self):
        """After round 5, registry should have >= 56 actions."""
        _reload()

        class FakeRegistry:
            def __init__(self):
                self.actions = []

            def register(self, name, **kwargs):
                self.actions.append(name)

        with patch.dict(
            sys.modules,
            {
                "maya": MagicMock(),
                "maya.cmds": MagicMock(),
                "maya.utils": MagicMock(),
                "dcc_mcp_core": MagicMock(
                    success_result=MagicMock(),
                    error_result=MagicMock(),
                ),
            },
        ):
            _reload()
            from dcc_mcp_maya.actions import register_all

            reg = FakeRegistry()
            register_all(reg)
            assert len(reg.actions) >= 56, (
                "Expected >= 56 actions after round 5, got {}".format(len(reg.actions))
            )

    def test_new_actions_in_all(self):
        """New round-5 actions are exported in __all__."""
        _reload()
        with patch.dict(
            sys.modules,
            {
                "maya": MagicMock(),
                "maya.cmds": MagicMock(),
                "maya.utils": MagicMock(),
                "dcc_mcp_core": MagicMock(
                    success_result=MagicMock(),
                    error_result=MagicMock(),
                ),
            },
        ):
            _reload()
            import dcc_mcp_maya.actions as pkg

            for name in ("assign_deformer", "create_blend_shape", "skin_cluster_bind",
                         "get_attribute", "set_attribute"):
                assert name in pkg.__all__, "{} missing from __all__".format(name)
