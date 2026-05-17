"""Shared helpers for Maya standalone E2E tests."""

from __future__ import annotations

import importlib.util
import json
import urllib.request
from pathlib import Path

import pytest

maya_standalone = pytest.importorskip(
    "maya.standalone",
    reason="maya.standalone not available — run under mayapy",
)

try:
    maya_standalone.initialize(name="python")
except Exception:
    pass

from maya import cmds  # noqa: E402


def _resolve_skills_root() -> Path:
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        package_dir = Path(dcc_mcp_maya.__file__).resolve().parent
        skills_dir = package_dir / "skills"
        if skills_dir.is_dir():
            return skills_dir
    except ImportError:
        pass

    src_skills = Path(__file__).resolve().parents[2] / "src" / "dcc_mcp_maya" / "skills"
    if src_skills.is_dir():
        return src_skills

    import os  # noqa: PLC0415

    env_dir = os.environ.get("DCC_MCP_MAYA_SKILL_PATHS", "")
    if env_dir:
        first = Path(env_dir.split(os.pathsep)[0])
        if first.is_dir():
            return first

    raise RuntimeError("Cannot find dcc_mcp_maya skills/ directory — check installation")


_SKILLS_ROOT = _resolve_skills_root()


def _ensure_package_importable() -> None:
    import sys  # noqa: PLC0415

    try:
        import dcc_mcp_maya  # noqa: F401

        return
    except ImportError:
        pass

    import os  # noqa: PLC0415

    mod_dir = os.environ.get("DCC_MCP_MAYA_MOD_DIR", "")
    if mod_dir:
        python_dir = Path(mod_dir) / "python"
        if python_dir.is_dir() and str(python_dir) not in sys.path:
            sys.path.insert(0, str(python_dir))


_ensure_package_importable()


def _new_scene():
    cmds.file(new=True, force=True)


def _load_script(skill_name: str, script_name: str):
    script_path = _SKILLS_ROOT / skill_name / "scripts" / f"{script_name}.py"
    spec = importlib.util.spec_from_file_location(script_name, script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mcp_post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read())


def _mcp_list_all_tools(url, request_id=100):
    tools = []
    cursor = None
    guard = 0
    while True:
        params = {"jsonrpc": "2.0", "id": request_id, "method": "tools/list"}
        if cursor:
            params["params"] = {"cursor": cursor}
        code, body = _mcp_post(url, params)
        assert code == 200
        result = body.get("result", {})
        tools.extend(result.get("tools", []))
        cursor = result.get("nextCursor")
        if not cursor:
            break
        guard += 1
        if guard > 50:
            raise RuntimeError("tools/list pagination exceeded 50 pages")
    return tools
