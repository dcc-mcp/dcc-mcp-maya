"""Regression tests for issue #608 — the arbitrary-script operator policy.

``DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1`` must refuse *every* code-bearing
tool, not just ``execute_python`` / ``execute_mel``. A Maya expression string is
code: ``cmds.expression(string='python("...")')`` evaluates the embedded Python
in the host. String filtering is not a substitute for a policy check at the
tool boundary.

All tests are host-free and synthetic. The fake ``maya.cmds`` records a purely
in-memory marker when it is asked to evaluate a marker payload — no scenes,
files or network are touched. With the policy enabled the marker must never be
set; with the policy disabled it must be set (proving the double really models
the vulnerable path).
"""

from __future__ import annotations

import builtins
import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
import yaml
from conftest import load_skill_script

from dcc_mcp_maya._env import ENV_DISABLE_ARBITRARY_SCRIPT

MARKER_ATTR = "_dcc_mcp_maya_608_marker"
# A MEL expression carrying an embedded python() payload, exactly the shape the
# reporter used. Only the in-memory marker is ever written by the fake host.
MARKER_EXPRESSION = 'python("import builtins; builtins.{} = True")'.format(MARKER_ATTR)
MARKER_SCRIPT_NODE = "import builtins; builtins.{} = True".format(MARKER_ATTR)


def _policy():
    """Import the policy module lazily so skill-level Red tests still run."""
    return importlib.import_module("dcc_mcp_maya._code_policy")


@pytest.fixture()
def fake_maya(monkeypatch):
    """Install a synthetic ``maya.cmds`` that models code evaluation in memory."""
    if hasattr(builtins, MARKER_ATTR):
        delattr(builtins, MARKER_ATTR)
    marker = {"expression_calls": 0, "script_node_calls": 0}

    maya_mod = types.ModuleType("maya")
    cmds = MagicMock(name="maya.cmds")
    cmds.objExists.return_value = True
    cmds.ls.return_value = []
    cmds.getAttr.return_value = ""
    cmds.delete.return_value = None

    def _expression(*args, **kwargs):
        marker["expression_calls"] += 1
        body = kwargs.get("string")
        if body is None and args and isinstance(args[0], str):
            body = args[0]
        if body and "python(" in str(body).lower():
            setattr(builtins, MARKER_ATTR, True)
        return "expressionNode1"

    def _script_node(**kwargs):
        marker["script_node_calls"] += 1
        body = kwargs.get("beforeScript") or ""
        if "builtins." in str(body):
            setattr(builtins, MARKER_ATTR, True)
        return "scriptNode1"

    cmds.expression.side_effect = _expression
    cmds.scriptNode.side_effect = _script_node
    maya_mod.cmds = cmds
    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    monkeypatch.delenv(ENV_DISABLE_ARBITRARY_SCRIPT, raising=False)
    yield cmds, marker
    if hasattr(builtins, MARKER_ATTR):
        delattr(builtins, MARKER_ATTR)


def _assert_refusal(result):
    assert result.get("success") is False, result
    assert "policy" in str(result.get("message", "")).lower(), result
    assert not hasattr(builtins, MARKER_ATTR), "marker was evaluated despite the policy"


# ---------------------------------------------------------------------------
# Red: code-bearing expression tools must obey the policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", ["create_expression", "edit_expression"])
@pytest.mark.parametrize("call", ["sdk", "main"])
def test_expression_tools_are_blocked_by_arbitrary_script_policy(fake_maya, entry, call):
    _cmds, marker = fake_maya
    mod = load_skill_script("maya-expressions", entry)
    kwargs = {"expression": MARKER_EXPRESSION}
    if entry == "edit_expression":
        kwargs["name"] = "expressionNode1"

    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        result = getattr(mod, entry)(**kwargs) if call == "sdk" else mod.main(**kwargs)

    _assert_refusal(result)
    assert marker["expression_calls"] == 0


@pytest.mark.parametrize("entry", ["create_expression", "edit_expression"])
def test_expression_tools_still_evaluate_when_policy_is_unset(fake_maya, entry):
    """Control: the fake host really models the vulnerable evaluation path."""
    _cmds, marker = fake_maya
    mod = load_skill_script("maya-expressions", entry)
    kwargs = {"expression": MARKER_EXPRESSION}
    if entry == "edit_expression":
        kwargs["name"] = "expressionNode1"

    result = getattr(mod, entry)(**kwargs)

    assert result.get("success") is True, result
    assert marker["expression_calls"] == 1
    assert getattr(builtins, MARKER_ATTR, False) is True


@pytest.mark.parametrize("call", ["sdk", "main"])
def test_script_node_create_is_blocked_by_arbitrary_script_policy(fake_maya, call):
    _cmds, marker = fake_maya
    mod = load_skill_script("maya-scripting", "get_script_node")
    kwargs = {"node_name": "markerScriptNode", "action": "create", "script": MARKER_SCRIPT_NODE}

    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        result = mod.get_script_node(**kwargs) if call == "sdk" else mod.main(**kwargs)

    _assert_refusal(result)
    assert marker["script_node_calls"] == 0


def test_script_node_create_still_writes_when_policy_is_unset(fake_maya):
    _cmds, marker = fake_maya
    mod = load_skill_script("maya-scripting", "get_script_node")
    result = mod.get_script_node(node_name="markerScriptNode", action="create", script=MARKER_SCRIPT_NODE)
    assert result.get("success") is True, result
    assert marker["script_node_calls"] == 1
    assert getattr(builtins, MARKER_ATTR, False) is True


def test_introspect_eval_is_blocked_by_arbitrary_script_policy(fake_maya):
    mod = load_skill_script("maya-scripting", "introspect")
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        result = mod.main(expression="1 + 2")
    _assert_refusal(result)


def test_introspect_eval_still_evaluates_when_policy_is_unset(fake_maya):
    mod = load_skill_script("maya-scripting", "introspect")
    result = mod.main(expression="1 + 2")
    assert result.get("success") is True, result
    assert "3" in str(result.get("context", {}))


# ---------------------------------------------------------------------------
# Normal, typed and read-only tools must remain available
# ---------------------------------------------------------------------------


def test_read_only_expression_query_is_not_blocked(fake_maya):
    mod = load_skill_script("maya-expressions", "list_expressions")
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        result = mod.main(object_name="")
    assert result.get("success") is True, result
    assert "policy" not in str(result.get("message", "")).lower()


def test_typed_animation_tools_are_not_in_the_code_bearing_inventory():
    policy = _policy()
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        assert policy.arbitrary_script_refusal("set_keyframes") is None
        assert policy.arbitrary_script_refusal("set_skin_weights") is None
        assert policy.arbitrary_script_refusal("list_expressions") is None


def test_policy_accepts_all_documented_truthy_tokens():
    policy = _policy()
    for token in ("1", "true", "yes", "on"):
        with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: token}):
            assert policy.resolve_arbitrary_script_disabled() is True
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "0"}):
        assert policy.resolve_arbitrary_script_disabled() is False


# ---------------------------------------------------------------------------
# Contract: the inventory is single-sourced and matches the shipped catalog
# ---------------------------------------------------------------------------

EXPECTED_CODE_BEARING_TOOLS = (
    "create_expression",
    "edit_expression",
    "execute_mel",
    "execute_python",
    "get_script_node",
    "introspect_eval",
    "write_module",
)


def test_code_bearing_inventory_is_pinned_and_matches_catalog():
    """Every code-bearing tool must exist in a shipped tools.yaml.

    This is the cross-DCC scope contract: the policy is a Maya-adapter-local
    tool allow/deny list, not a Core-wide sandbox. Adding a new code-bearing
    tool without extending the inventory fails here.
    """
    policy = _policy()
    assert tuple(sorted(policy.CODE_BEARING_TOOLS)) == EXPECTED_CODE_BEARING_TOOLS
    assert policy.POLICY_SCOPE == "maya_adapter_tool_surface"

    catalog_names = set()
    skills_dir = os.path.join(os.path.dirname(policy.__file__), "skills")
    for root, _dirs, files in os.walk(skills_dir):
        if "tools.yaml" not in files:
            continue
        with open(os.path.join(root, "tools.yaml"), "r", encoding="utf-8") as handle:
            spec = yaml.safe_load(handle) or {}
        for tool in spec.get("tools") or []:
            if tool.get("name"):
                catalog_names.add(tool["name"])
    missing = set(policy.CODE_BEARING_TOOLS) - catalog_names
    assert not missing, "inventory names absent from tools.yaml: {}".format(sorted(missing))


@pytest.mark.parametrize("tool", EXPECTED_CODE_BEARING_TOOLS)
def test_every_code_bearing_tool_refuses_under_policy(tool):
    policy = _policy()
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        refusal = policy.arbitrary_script_refusal(tool)
    assert refusal is not None
    assert refusal.get("success") is False
    assert "policy" in str(refusal.get("message", "")).lower()


def test_non_code_bearing_tool_is_never_refused():
    policy = _policy()
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        assert policy.arbitrary_script_refusal("maya_primitives__create_sphere") is None
    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "0"}):
        assert policy.arbitrary_script_refusal("create_expression") is None


def test_policy_is_adapter_local_and_never_claims_to_be_a_sandbox():
    """Cross-DCC scope contract: no Core / gateway / host coupling.

    The policy is a Maya-adapter-local allow/deny list. Other dcc-mcp-*
    adapters keep their own execution policies; no shared Core contract is
    introduced, so no separate Core dependency PR is required.
    """
    import ast

    policy = _policy()
    assert policy.POLICY_SCOPE == "maya_adapter_tool_surface"
    assert not any(word in policy.POLICY_SCOPE for word in ("sandbox", "global", "core"))

    source = open(policy.__file__, "r", encoding="utf-8").read()
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "dcc_mcp_maya" in imported
    assert not (imported & {"socket", "urllib", "requests", "http", "subprocess"})
    assert "server" not in imported and "gateway" not in imported

    with patch.dict(os.environ, {ENV_DISABLE_ARBITRARY_SCRIPT: "1"}):
        refusal = policy.arbitrary_script_refusal("create_expression")
    ctx = refusal.get("context") or {}
    assert ctx.get("policy_scope") == policy.POLICY_SCOPE
    assert ctx.get("tool_name") == "create_expression"
