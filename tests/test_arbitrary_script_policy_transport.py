"""Transport-level regression for issue #608 (MCP Streamable HTTP).

Exercises the real agent path, not just the SDK functions:

1. ``initialize`` + ``tools/list`` — discovery must still work in restricted
   mode (normal tools and ``load_skill`` remain advertised).
2. ``tools/call load_skill`` — the expressions skill expands, so the typed
   ``create_expression`` tool becomes directly invocable.
3. ``tools/call create_expression`` with a marker payload — with
   ``DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1`` the call must be refused *before*
   it reaches Maya, and the purely in-memory marker must stay absent.
4. A control run with the flag unset proves the same transport path really does
   reach the fake host and would evaluate the payload (so test 3 is not
   vacuously passing on a dead dispatch path).
5. A read-only tool from the same skill stays callable in restricted mode.

Headless note
=============

The shipped expression tools declare ``affinity: main``; without a live Maya
main-thread pump the Rust readiness gate refuses to queue them. To keep this a
real transport test we materialise a temporary skill overlay whose
``tools.yaml`` sets ``affinity: any`` and whose ``scripts/*.py`` are **byte-
identical copies** of the shipped files (asserted below). That is the only
test-only difference — the code under test is the real shipped script, reached
through real MCP ``tools/list`` -> ``load_skill`` -> ``tools/call``.

The fake ``maya.cmds`` writes only a Python builtins attribute — no scene,
file, network or real host is touched.
"""

from __future__ import annotations

import builtins
import json
import os
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from dcc_mcp_maya._env import ENV_DISABLE_ARBITRARY_SCRIPT
from dcc_mcp_maya.server import MayaMcpServer
from tests._transport_support import mcp_initialize, mcp_list_all_tools, mcp_post

MARKER_ATTR = "_dcc_mcp_maya_608_transport_marker"
MARKER_EXPRESSION = 'python("import builtins; builtins.{} = True")'.format(MARKER_ATTR)
SKILL_NAME = "maya-expressions"

SHIPPED_SKILL = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / SKILL_NAME


def _build_headless_overlay(root: Path) -> Path:
    """Copy the shipped skill verbatim, relaxing only tool affinity."""
    dst = root / SKILL_NAME
    (dst / "scripts").mkdir(parents=True)
    (dst / "SKILL.md").write_bytes((SHIPPED_SKILL / "SKILL.md").read_bytes())
    (dst / "groups.yaml").write_bytes((SHIPPED_SKILL / "groups.yaml").read_bytes())

    spec = yaml.safe_load((SHIPPED_SKILL / "tools.yaml").read_text(encoding="utf-8"))
    for tool in spec.get("tools") or []:
        tool["affinity"] = "any"
    (dst / "tools.yaml").write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    for script in sorted((SHIPPED_SKILL / "scripts").glob("*.py")):
        (dst / "scripts" / script.name).write_bytes(script.read_bytes())
    return dst


def _assert_overlay_is_byte_identical(overlay: Path):
    for script in sorted((SHIPPED_SKILL / "scripts").glob("*.py")):
        assert (overlay / "scripts" / script.name).read_bytes() == script.read_bytes(), script.name


def _install_fake_maya(monkeypatch):
    if hasattr(builtins, MARKER_ATTR):
        delattr(builtins, MARKER_ATTR)
    marker = {"expression_calls": 0}
    maya_mod = types.ModuleType("maya")
    cmds = MagicMock(name="maya.cmds")
    cmds.objExists.return_value = True
    cmds.ls.return_value = []

    def _expression(*args, **kwargs):
        marker["expression_calls"] += 1
        body = kwargs.get("string")
        if body and "python(" in str(body).lower():
            setattr(builtins, MARKER_ATTR, True)
        return "expressionNode1"

    cmds.expression.side_effect = _expression
    maya_mod.cmds = cmds
    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    return marker


def _tools_call(mcp_url, session, name, arguments, request_id=300):
    response = mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        session_id=session,
    )
    assert "result" in response, "tools/call {} failed: {}".format(name, response)
    result = response["result"]
    content = result.get("content") or []
    assert content, "tools/call {} returned empty content: {}".format(name, result)
    text = content[0].get("text", "")
    try:
        envelope = json.loads(text)
    except json.JSONDecodeError:
        envelope = {"raw": text}
    envelope["__is_error__"] = result.get("isError")
    return envelope


@pytest.fixture(params=["1", "0"], ids=["restricted", "unrestricted"])
def transport(request, monkeypatch, tmp_path):
    """Start one in-process MCP server with the flag set before Maya init."""
    if request.param == "1":
        monkeypatch.setenv(ENV_DISABLE_ARBITRARY_SCRIPT, "1")
    else:
        monkeypatch.delenv(ENV_DISABLE_ARBITRARY_SCRIPT, raising=False)
    marker = _install_fake_maya(monkeypatch)

    overlay = _build_headless_overlay(tmp_path)
    _assert_overlay_is_byte_identical(overlay)

    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(extra_skill_paths=[str(tmp_path)], include_bundled=False, minimal=True)
    handle = server.start()
    time.sleep(0.05)
    # No live Maya main thread exists; mark the synthetic host ready so the
    # readiness gate admits the call. The overlay's ``affinity: any`` then keeps
    # execution inline on the HTTP worker instead of queueing to a host pump.
    server.readiness.mark_dcc_ready(True)
    assert server.readiness_report()["dcc"] is True
    try:
        session = mcp_initialize(handle.mcp_url())
        yield {
            "url": handle.mcp_url(),
            "session": session,
            "marker": marker,
            "restricted": request.param == "1",
            "env": dict(os.environ),
        }
    finally:
        server.stop()
        if hasattr(builtins, MARKER_ATTR):
            delattr(builtins, MARKER_ATTR)


def test_expression_policy_over_mcp_discovery_and_direct_invocation(transport):
    url = transport["url"]
    session = transport["session"]

    # 1. Discovery still works: meta tools are advertised, skill tools are not
    #    expanded yet in minimal mode.
    before = [t["name"] for t in mcp_list_all_tools(url, session_id=session, request_id=100)]
    assert "load_skill" in before, sorted(before)
    assert "create_expression" not in before

    # 2. Loading the skill exposes the typed tool for direct invocation.
    load = _tools_call(url, session, "load_skill", {"skill_name": SKILL_NAME}, request_id=200)
    assert load.get("__is_error__") is not True, load
    after = [t["name"] for t in mcp_list_all_tools(url, session_id=session, request_id=400)]
    assert "create_expression" in after, sorted(after)

    # 3. The code-bearing call is refused before reaching the host when the
    #    policy is on; the control run proves the dispatch path really reaches
    #    the fake host when the policy is off.
    result = _tools_call(
        url,
        session,
        "create_expression",
        {"expression": MARKER_EXPRESSION},
        request_id=500,
    )
    if transport["restricted"]:
        assert result.get("success") is False, result
        assert "policy" in str(result.get("message", "")).lower(), result
        assert transport["marker"]["expression_calls"] == 0
        assert not hasattr(builtins, MARKER_ATTR), "marker leaked despite the policy"
    else:
        assert result.get("success") is True, result
        assert transport["marker"]["expression_calls"] == 1
        assert getattr(builtins, MARKER_ATTR, False) is True

    # 4. Normal read-only tools from the same skill stay available.
    listed = _tools_call(url, session, "list_expressions", {}, request_id=600)
    assert listed.get("success") is True, listed
    assert "policy" not in str(listed.get("message", "")).lower()


def test_flag_is_set_before_server_start(transport):
    """The reporter's deployment: flag set before Maya/server initialisation."""
    if transport["restricted"]:
        assert transport["env"].get(ENV_DISABLE_ARBITRARY_SCRIPT) == "1"
    else:
        assert transport["env"].get(ENV_DISABLE_ARBITRARY_SCRIPT) is None
