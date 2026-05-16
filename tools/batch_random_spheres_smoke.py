"""Smoke test: 10 random spheres → group → export FBX (main-thread safe for HTTP)."""

from __future__ import annotations

import os
import random
from typing import List

import maya.cmds as cmds
import maya.mel as mel
import maya.utils as utils

COUNT = 10
RADIUS_MIN = 0.15
RADIUS_MAX = 0.45
SPREAD = 8.0
NAME_PREFIX = "mcp_random_sphere_"
GROUP_NAME = "mcp_random_spheres_grp"
FBX_BASENAME = "mcp_random_spheres_batch.fbx"
# Override via env for quick tests, e.g. DCC_MCP_SMOKE_FBX=C:/test.fbx
FBX_OVERRIDE = os.environ.get("DCC_MCP_SMOKE_FBX", "").strip()


def _resolve_fbx_path() -> str:
    if FBX_OVERRIDE:
        return FBX_OVERRIDE.replace("\\", "/")
    scene_path = cmds.file(query=True, sceneName=True) or ""
    if scene_path:
        directory = os.path.dirname(scene_path)
    else:
        directory = cmds.internalVar(userTmpDir=True)
    return os.path.join(directory, FBX_BASENAME).replace("\\", "/")


def _cleanup_prior_run() -> None:
    prior = cmds.ls(NAME_PREFIX + "*", type="transform") or []
    if prior:
        cmds.delete(prior)
    old_group = cmds.ls(GROUP_NAME, type="transform") or []
    if old_group:
        cmds.delete(old_group)


def _run_batch() -> str:
    _cleanup_prior_run()

    created: List[str] = []
    for index in range(COUNT):
        radius = random.uniform(RADIUS_MIN, RADIUS_MAX)
        node, _shape = cmds.polySphere(radius=radius, name="{}{:02d}".format(NAME_PREFIX, index + 1))
        cmds.move(
            random.uniform(-SPREAD, SPREAD),
            random.uniform(0.0, SPREAD * 0.5),
            random.uniform(-SPREAD, SPREAD),
            node,
        )
        created.append(node)

    group = cmds.group(created, name=GROUP_NAME)
    cmds.select(group, replace=True)

    fbx_path = _resolve_fbx_path()
    parent = os.path.dirname(fbx_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya")

    mel.eval("FBXResetExport")
    cmds.file(
        fbx_path,
        force=True,
        options="v=0;",
        type="FBX export",
        exportSelected=True,
    )

    if not os.path.isfile(fbx_path):
        raise RuntimeError("FBX missing after export: {}".format(fbx_path))
    size = os.path.getsize(fbx_path)
    return (
        "BATCH_SPHERES_OK count={} group={} fbx={} size_bytes={} nodes={}".format(
            len(created),
            group,
            fbx_path,
            size,
            ",".join(created),
        )
    )


print(utils.executeInMainThreadWithResult(_run_batch))
