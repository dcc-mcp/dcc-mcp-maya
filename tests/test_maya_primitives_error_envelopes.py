"""Negative-path contracts for maya-primitives skills."""

from __future__ import annotations

import types
from unittest.mock import patch

from tests.conftest import load_skill_script


class _CmdsWithMissingNodes:
    def objExists(self, _name):  # noqa: N802
        return False


class _CmdsWithOneNode:
    def __init__(self):
        self.attrs = []

    def objExists(self, name):  # noqa: N802
        return name == "pCube1"

    def setAttr(self, *args, **kwargs):  # noqa: N802
        self.attrs.append((args, kwargs))


def _with_cmds(cmds):
    return patch.dict("sys.modules", {"maya": types.ModuleType("maya"), "maya.cmds": cmds})


def test_get_transform_missing_node_returns_structured_error():
    mod = load_skill_script("maya-primitives", "get_transform")

    with _with_cmds(_CmdsWithMissingNodes()):
        result = mod.get_transform(object_name="missingCube")

    assert result["success"] is False
    assert result["message"] == "Node not found: missingCube"
    assert result["context"]["possible_solutions"]


def test_rename_object_missing_node_returns_structured_error():
    mod = load_skill_script("maya-primitives", "rename_object")

    with _with_cmds(_CmdsWithMissingNodes()):
        result = mod.rename_object(object_name="missingCube", new_name="newCube")

    assert result["success"] is False
    assert result["message"] == "Node not found: missingCube"
    assert result["context"]["possible_solutions"]


def test_set_transform_rejects_short_translate_vector_without_mutating():
    mod = load_skill_script("maya-primitives", "set_transform")
    cmds = _CmdsWithOneNode()

    with _with_cmds(cmds):
        result = mod.set_transform(object_name="pCube1", translate=[1.0, 2.0])

    assert result["success"] is False
    assert result["message"] == "Invalid transform vector: translate"
    assert result["context"]["parameter"] == "translate"
    assert result["context"]["possible_solutions"]
    assert cmds.attrs == []


def test_set_transform_rejects_non_numeric_vector_without_mutating():
    mod = load_skill_script("maya-primitives", "set_transform")
    cmds = _CmdsWithOneNode()

    with _with_cmds(cmds):
        result = mod.set_transform(object_name="pCube1", rotate=[0.0, "bad", 1.0])

    assert result["success"] is False
    assert result["message"] == "Invalid transform vector: rotate"
    assert "numeric" in result["error"]
    assert cmds.attrs == []
