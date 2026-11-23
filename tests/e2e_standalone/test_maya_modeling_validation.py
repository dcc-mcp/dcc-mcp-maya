"""Minimal real-Maya smoke coverage for model-state validation."""

from __future__ import annotations

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e


def test_model_state_export_and_uv_verification_in_real_maya():
    _new_scene()
    create = _load_script("maya-primitives", "create_cube")
    export = _load_script("maya-modeling-validation", "export_model_state")
    verify = _load_script("maya-modeling-validation", "verify_modeling_operation")

    created = create.create_cube(name="modelStateSmoke")
    assert created["success"] is True, created

    state_result = export.export_model_state(object_names=["modelStateSmoke"])
    assert state_result["success"] is True, state_result
    state = state_result["context"]["state"]
    assert state["schema_name"] == "dcc-mcp/model-state"
    assert state["meshes"]
    assert state["meshes"][0]["vertex_count"] > 0

    uv_result = verify.verify_modeling_operation(
        object_name="modelStateSmoke",
        operation="uv",
        expected={"min_uv_count": 1},
    )
    assert uv_result["success"] is True, uv_result
    assert uv_result["context"]["status"] == "pass"
    assert cmds.objExists("modelStateSmoke")
