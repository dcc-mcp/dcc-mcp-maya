"""Primitive creation skills return stable node context."""

from __future__ import annotations

import types
from unittest.mock import patch

from tests.conftest import load_skill_script


class _PrimitiveCmds:
    def polyCube(self, **_kwargs):  # noqa: N802
        return ["pCube1", "polyCube1"]

    def polySphere(self, **_kwargs):  # noqa: N802
        return ["pSphere1", "polySphere1"]

    def polyCylinder(self, **_kwargs):  # noqa: N802
        return ["pCylinder1", "polyCylinder1"]

    def polyPlane(self, **_kwargs):  # noqa: N802
        return ["pPlane1", "polyPlane1"]

    def rename(self, _old, new):
        return new

    def ls(self, name, long=False, uuid=False):  # noqa: A002 - mirrors maya.cmds flag name
        if uuid:
            short = str(name).rsplit("|", 1)[-1]
            return ["uuid-{}".format(short)]
        return ["|{}".format(name)] if long and not str(name).startswith("|") else [name]

    def listRelatives(self, name, shapes=False, fullPath=False):  # noqa: N803
        if shapes and fullPath:
            return ["{}Shape".format(name)]
        return []

    def objectType(self, _name):  # noqa: N802
        return "transform"

    def nodeType(self, _name):  # noqa: N802
        return "transform"

    def objExists(self, _name):  # noqa: N802
        return True

    def file(self, query=False, sceneName=False):  # noqa: N803
        if query and sceneName:
            return "C:/show/primitive.ma"
        return ""

    def getAttr(self, attr):  # noqa: N802
        if attr.endswith(".translate"):
            return [(0, 0, 0)]
        if attr.endswith(".rotate"):
            return [(0, 0, 0)]
        if attr.endswith(".scale"):
            return [(1, 1, 1)]
        raise RuntimeError(attr)

    def exactWorldBoundingBox(self, _name):  # noqa: N802
        return [-0.5, -0.5, -0.5, 0.5, 0.5, 0.5]


def test_primitive_create_tools_return_rich_node_context():
    cmds = _PrimitiveCmds()
    with patch.dict("sys.modules", {"maya": types.ModuleType("maya"), "maya.cmds": cmds}):
        cases = [
            ("create_cube", "create_cube", {"name": "unitCube"}),
            ("create_sphere", "create_sphere", {"name": "unitSphere"}),
            ("create_cylinder", "create_cylinder", {"name": "unitCylinder"}),
            ("create_plane", "create_plane", {"name": "unitPlane"}),
        ]
        for script_name, function_name, kwargs in cases:
            mod = load_skill_script("maya-primitives", script_name)
            result = getattr(mod, function_name)(**kwargs)

            context = result["context"]
            assert result["success"] is True
            assert context["object_name"] == kwargs["name"]
            assert context["long_name"] == "|{}".format(kwargs["name"])
            assert context["node"]["shape_names"] == ["|{}Shape".format(kwargs["name"])]
            assert context["node"]["transform"]["scale"] == [1.0, 1.0, 1.0]
            assert context["node_ref"]["uuid"] == "uuid-{}".format(kwargs["name"])
            assert context["node_ref"]["exists"] is True
            assert context["node_ref"]["stale"] is False
