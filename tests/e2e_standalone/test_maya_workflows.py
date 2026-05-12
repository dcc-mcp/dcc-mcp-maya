"""Maya standalone E2E tests."""

from __future__ import annotations

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e


class TestRiggingWorkflow:
    """Multi-step rigging workflows: joints, skin, IK, blend shapes."""

    def setup_method(self):
        _new_scene()

    def test_joint_chain_and_skin_bind(self):
        """Create a cube, a 3-joint chain, then bind skin — verify skinCluster."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        joint_mod = _load_script("maya-rigging", "create_joint")
        bind_mod = _load_script("maya-rigging", "skin_cluster_bind")

        cube_mod.create_cube(name="skinMesh")

        # Root joint at origin
        r = joint_mod.create_joint(name="jntRoot", position=[0.0, 0.0, 0.0])
        assert r["success"] is True
        # Mid joint
        r = joint_mod.create_joint(name="jntMid", position=[0.0, 2.0, 0.0], parent="jntRoot")
        assert r["success"] is True
        # Tip joint
        r = joint_mod.create_joint(name="jntTip", position=[0.0, 4.0, 0.0], parent="jntMid")
        assert r["success"] is True

        bind_result = bind_mod.skin_cluster_bind(
            joints=["jntRoot", "jntMid", "jntTip"],
            mesh="skinMesh",
            max_influences=3,
        )
        assert bind_result["success"] is True
        # A skinCluster node must exist
        assert len(cmds.ls(type="skinCluster")) > 0

    def test_ik_handle_on_joint_chain(self):
        """Create a joint chain then apply an IK handle — verify node exists."""
        joint_mod = _load_script("maya-rigging", "create_joint")
        ik_mod = _load_script("maya-rigging", "create_ik_handle")

        joint_mod.create_joint(name="ikRoot", position=[0.0, 0.0, 0.0])
        joint_mod.create_joint(name="ikMid", position=[0.0, 2.0, 0.0], parent="ikRoot")
        joint_mod.create_joint(name="ikTip", position=[0.0, 4.0, 0.0], parent="ikMid")

        ik_result = ik_mod.create_ik_handle(
            start_joint="ikRoot",
            end_joint="ikTip",
            name="testIK",
        )
        assert ik_result["success"] is True
        assert cmds.objExists("testIK")

    def test_blend_shape_workflow(self):
        """Base + target spheres → blend shape node created."""
        sphere_mod = _load_script("maya-primitives", "create_sphere")
        set_tf_mod = _load_script("maya-primitives", "set_transform")
        bs_mod = _load_script("maya-rigging", "create_blend_shape")

        sphere_mod.create_sphere(name="bsBase")
        sphere_mod.create_sphere(name="bsTarget")
        # Move target so it's distinguishable
        set_tf_mod.set_transform(object_name="bsTarget", translate=[5.0, 0.0, 0.0])

        bs_result = bs_mod.create_blend_shape(
            base_mesh="bsBase",
            target_meshes=["bsTarget"],
            name="testBlendShape",
        )
        assert bs_result["success"] is True
        assert len(cmds.ls(type="blendShape")) > 0


class TestAnimationWorkflow:
    """Multi-attribute keyframe sequences, timeline, bake, curve queries."""

    def setup_method(self):
        _new_scene()

    def test_multi_attribute_keyframe_sequence(self):
        """Key tx and ty on multiple frames, verify keyframe lists."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        set_kf_mod = _load_script("maya-animation", "set_keyframe")
        get_kf_mod = _load_script("maya-animation", "get_keyframes")

        cube_mod.create_cube(name="multiAnimCube")

        # translateX: 0 at frame 1, 10 at frame 24
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateX", time=1, value=0.0)
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateX", time=24, value=10.0)
        # translateY: 0 at frame 1, 5 at frame 12
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateY", time=1, value=0.0)
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateY", time=12, value=5.0)

        tx_keys = get_kf_mod.get_keyframes(object_name="multiAnimCube", attribute="translateX")
        assert tx_keys["success"] is True
        keys = tx_keys["context"].get("keyframes", [])
        assert 1 in keys or 1.0 in keys
        assert 24 in keys or 24.0 in keys

        ty_keys = get_kf_mod.get_keyframes(object_name="multiAnimCube", attribute="translateY")
        assert ty_keys["success"] is True
        assert len(ty_keys["context"].get("keyframes", [])) >= 2

    def test_set_current_time_and_query(self):
        """set_current_time then get_current_time returns correct frame."""
        set_mod = _load_script("maya-animation", "set_current_time")
        get_mod = _load_script("maya-animation", "get_current_time")

        set_result = set_mod.set_current_time(frame=15)
        assert set_result["success"] is True

        get_result = get_mod.get_current_time()
        assert get_result["success"] is True
        assert abs(get_result["context"]["current_time"] - 15.0) < 0.01

    def test_timeline_and_bake_simulation(self):
        """Set timeline, add keyframes, bake, verify animation curves exist."""
        tl_mod = _load_script("maya-animation", "set_timeline")
        loc_mod = _load_script("maya-scene", "create_locator")
        set_kf_mod = _load_script("maya-animation", "set_keyframe")
        bake_mod = _load_script("maya-animation", "bake_simulation")
        list_mod = _load_script("maya-animation", "list_animation_curves")

        tl_mod.set_timeline(start_frame=1, end_frame=48)
        loc_mod.create_locator(name="bakeLoc")

        set_kf_mod.set_keyframe(object_name="bakeLoc", attribute="translateX", time=1, value=0.0)
        set_kf_mod.set_keyframe(object_name="bakeLoc", attribute="translateX", time=48, value=10.0)

        bake_result = bake_mod.bake_simulation(
            objects=["bakeLoc"],
            start_frame=1.0,
            end_frame=48.0,
            sample_by=1.0,
        )
        assert bake_result["success"] is True

        curves = list_mod.list_animation_curves(object_name="bakeLoc")
        assert curves["success"] is True
        assert len(curves["context"].get("curves", [])) > 0


class TestMeshAndMaterialWorkflow:
    """Subdivision, merge, cleanup, UV ops, material assignment chain."""

    def setup_method(self):
        _new_scene()

    def test_mesh_ops_chain(self):
        """Sphere → subdivision → get_poly_count > baseline → merge → cleanup."""
        sphere_mod = _load_script("maya-primitives", "create_sphere")
        subdiv_mod = _load_script("maya-mesh-ops", "apply_subdivision")
        count_mod = _load_script("maya-mesh-ops", "get_poly_count")
        merge_mod = _load_script("maya-mesh-ops", "merge_vertices")
        cleanup_mod = _load_script("maya-mesh-ops", "cleanup_mesh")

        sphere_mod.create_sphere(name="meshSphere")

        # Baseline poly count
        before = count_mod.get_poly_count("meshSphere")
        assert before["success"] is True
        base_faces = before["context"].get("faces", 0)

        # Subdivide → more polygons
        subdiv_mod.apply_subdivision(object_name="meshSphere", level=1, method="preview")
        after = count_mod.get_poly_count("meshSphere")
        assert after["success"] is True
        assert after["context"].get("faces", 0) >= base_faces

        # Merge and cleanup don't crash
        merge_mod.merge_vertices(object_name="meshSphere", threshold=0.001)
        cleanup_mod.cleanup_mesh(object_name="meshSphere")

    def test_material_and_uv_workflow(self):
        """Create plane → blinn material → assign → UV set → project → query."""
        plane_mod = _load_script("maya-primitives", "create_plane")
        mat_mod = _load_script("maya-materials", "create_material")
        assign_mod = _load_script("maya-materials", "assign_material")
        uv_set_mod = _load_script("maya-uv-ops", "create_uv_set")
        project_mod = _load_script("maya-uv-ops", "project_uvs")
        uv_info_mod = _load_script("maya-uv-ops", "get_uv_info")
        shader_mod = _load_script("maya-materials", "get_shader_assignment")

        plane_mod.create_plane(name="uvPlane")

        mat_result = mat_mod.create_material(material_type="blinn", name="testBlinn")
        assert mat_result["success"] is True

        assign_mod.assign_material(material_name="testBlinn", objects=["uvPlane"])

        uv_set_mod.create_uv_set(object_name="uvPlane", uv_set_name="myUVSet")
        project_mod.project_uvs(object_name="uvPlane", projection_type="planar", axis="y")

        uv_info = uv_info_mod.get_uv_info(object_name="uvPlane")
        assert uv_info["success"] is True

        shader_info = shader_mod.get_shader_assignment(object_name="uvPlane")
        assert shader_info["success"] is True

    def test_rename_and_group_workflow(self):
        """Create cubes → rename → group → parent → verify hierarchy."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        rename_mod = _load_script("maya-primitives", "rename_object")
        group_mod = _load_script("maya-scene", "group_objects")
        parent_mod = _load_script("maya-scene", "parent_object")

        cube_mod.create_cube(name="cubeA")
        cube_mod.create_cube(name="cubeB")

        ren = rename_mod.rename_object(object_name="cubeA", new_name="cubeRenamed")
        assert ren["success"] is True
        assert cmds.objExists("cubeRenamed")

        grp = group_mod.group_objects(objects=["cubeRenamed"], group_name="myGroup")
        assert grp["success"] is True
        assert cmds.objExists("myGroup")

        # Parent cubeB under myGroup
        par = parent_mod.parent_object(child="cubeB", parent="myGroup")
        assert par["success"] is True
        assert cmds.listRelatives("cubeB", parent=True)[0] == "myGroup"


class TestNodeGraphWorkflow:
    """Attribute ops, connect/disconnect, expressions, display layers."""

    def setup_method(self):
        _new_scene()

    def test_add_and_connect_attribute(self):
        """Add float attr to cube A, connect to cube B translateX, then disconnect."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        add_attr_mod = _load_script("maya-attributes", "add_attribute")
        connect_mod = _load_script("maya-node-graph", "connect_attr")
        list_conn_mod = _load_script("maya-node-graph", "list_connections")
        disconnect_mod = _load_script("maya-node-graph", "disconnect_attr")

        cube_mod.create_cube(name="srcCube")
        cube_mod.create_cube(name="dstCube")

        add_result = add_attr_mod.add_attribute(
            node_name="srcCube",
            attribute="myFloat",
            attr_type="float",
            keyable=True,
        )
        assert add_result["success"] is True

        connect_result = connect_mod.connect_attr(
            source_attr="srcCube.myFloat",
            dest_attr="dstCube.translateX",
            force=True,
        )
        assert connect_result["success"] is True

        # Verify connection exists
        conns = list_conn_mod.list_connections(object_name="dstCube", attribute="translateX")
        assert conns["success"] is True
        assert len(conns["context"].get("connections", [])) > 0

        # Disconnect
        disc = disconnect_mod.disconnect_attr(
            source_attr="srcCube.myFloat",
            dest_attr="dstCube.translateX",
        )
        assert disc["success"] is True

    def test_expression_driven_value(self):
        """Create expression driving tx = frame*0.1 → verify at frame 10."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        expr_mod = _load_script("maya-expressions", "create_expression")
        list_expr_mod = _load_script("maya-expressions", "list_expressions")
        set_time_mod = _load_script("maya-animation", "set_current_time")
        get_tf_mod = _load_script("maya-primitives", "get_transform")
        del_expr_mod = _load_script("maya-expressions", "delete_expression")

        cube_mod.create_cube(name="exprCube")

        expr_result = expr_mod.create_expression(
            expression="exprCube.translateX = frame * 0.1;",
            name="testExpr",
        )
        assert expr_result["success"] is True

        exprs = list_expr_mod.list_expressions()
        assert exprs["success"] is True
        names = [e.get("name", "") for e in exprs["context"].get("expressions", [])]
        assert "testExpr" in names

        set_time_mod.set_current_time(frame=10)
        tf = get_tf_mod.get_transform(object_name="exprCube")
        assert tf["success"] is True
        tx = tf["context"]["translate"][0]
        assert abs(tx - 1.0) < 0.1  # frame 10 * 0.1 ≈ 1.0

        del_expr_mod.delete_expression(expression_name="testExpr")

    def test_display_layer_workflow(self):
        """Create display layer, add objects, list layers, delete."""
        sphere_mod = _load_script("maya-primitives", "create_sphere")
        dl_create_mod = _load_script("maya-display", "create_display_layer")
        dl_set_mod = _load_script("maya-display", "set_display_layer")
        dl_list_mod = _load_script("maya-display", "list_display_layers")
        dl_delete_mod = _load_script("maya-display", "delete_display_layer")

        sphere_mod.create_sphere(name="dlSphere1")
        sphere_mod.create_sphere(name="dlSphere2")

        create_result = dl_create_mod.create_display_layer(name="testLayer")
        assert create_result["success"] is True

        set_result = dl_set_mod.set_display_layer(
            layer_name="testLayer",
            objects=["dlSphere1", "dlSphere2"],
        )
        assert set_result["success"] is True

        list_result = dl_list_mod.list_display_layers()
        assert list_result["success"] is True
        layer_names = [lay.get("name", "") for lay in list_result["context"].get("layers", [])]
        assert "testLayer" in layer_names

        del_result = dl_delete_mod.delete_display_layer(layer_name="testLayer")
        assert del_result["success"] is True
        layer_names_after = [
            lay.get("name", "") for lay in dl_list_mod.list_display_layers()["context"].get("layers", [])
        ]
        assert "testLayer" not in layer_names_after
