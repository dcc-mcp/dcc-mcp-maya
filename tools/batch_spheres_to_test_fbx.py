"""Minimal batch: 10 random spheres, group, export C:/test.fbx (main-thread safe).

dcc-mcp HTTP ``execute_python`` may run off Maya's UI thread; ``cmds.file``
FBX export and ``loadPlugin`` must run on the main thread or Maya can crash.
This matches the maya-mcp-server pattern: do real ``cmds`` work inside
``maya.utils.executeInMainThreadWithResult``.
"""

from __future__ import annotations

import os
import random
from typing import List

import maya.cmds as cmds
import maya.mel as mel
import maya.utils as utils

FBX_PATH = "C:/test.fbx"
COUNT = 10


def _build_and_export() -> str:
    created: List[str] = []
    for index in range(COUNT):
        radius = random.uniform(0.2, 0.5)
        node, _shape = cmds.polySphere(radius=radius, name="mcp_sphere_{:02d}".format(index + 1))
        cmds.move(
            random.uniform(-5.0, 5.0),
            random.uniform(0.0, 3.0),
            random.uniform(-5.0, 5.0),
            node,
        )
        created.append(node)

    group = cmds.group(created, name="mcp_sphere_grp")
    cmds.select(group, replace=True)

    if not os.path.isdir("C:/"):
        raise RuntimeError("C:/ is not available on this machine")

    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya")

    mel.eval("FBXResetExport")
    cmds.file(
        FBX_PATH,
        force=True,
        options="v=0;",
        type="FBX export",
        exportSelected=True,
    )

    if not os.path.isfile(FBX_PATH):
        raise RuntimeError("FBX missing after export: {}".format(FBX_PATH))
    size = os.path.getsize(FBX_PATH)
    return "OK count={} group={} fbx={} bytes={}".format(len(created), group, FBX_PATH, size)


print(utils.executeInMainThreadWithResult(_build_and_export))
