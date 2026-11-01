"""Adapter-local policy for tools that evaluate arbitrary code (issue #608).

What this is
============

``DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1`` means **"disallow arbitrary code
evaluation across this adapter's code-bearing tool surface"**. A tool is
code-bearing when a caller-supplied string is handed, unmodified, to a Maya
code-evaluation API (``cmds.expression(string=...)``,
``cmds.scriptNode(beforeScript=...)``, ``exec``/``eval``, ``runpy.run_path``,
an arbitrary imported callable, ``cmds.loadPlugin``, or ``mel.eval`` of a whole
user string). A MEL expression may embed ``python(...)`` and therefore executes
Python in the host; filtering the string is not a substitute for a policy check
at the tool boundary.

The development entry points are a separate policy surface, not an exception:
``maya-dev`` ``run_script`` / ``run_entrypoint`` / ``run_check`` /
``reload_modules`` / ``start_debugpy`` execute or import project code inside
Maya, so they are gated too. ``attach_project`` only registers a trusted root
(controlled by ``DCC_MCP_MAYA_DEV_ROOTS``) and stays available, but every tool
that actually runs code from that root is refused. ``load_plugin`` is gated
because loading a plug-in introduces new native code; ``unload_plugin`` and
``list_plugins`` remain available because they only remove or inspect code.

What this is NOT
================

* **Not a sandbox.** It does not restrict Python or MEL inside Maya. It refuses
  the enumerated tool entry points before they reach the host.
* **Not a Core / cross-DCC contract.** Other ``dcc-mcp-*`` adapters have their
  own execution policies; ``dcc-mcp-core`` exposes no global sandbox switch.
  This module is deliberately Maya-adapter-local and imports no host, network
  or gateway APIs.
* **Not protection against code already inside a session.** Already-loaded
  plug-ins, embedded scene-file script nodes, ``userSetup.py``, scene callbacks,
  gateway-side dispatch and anything else that reaches Maya's interpreter
  outside these tool entry points are out of scope. A *new* call through a
  gated tool is in scope regardless of where its code came from.
* **Not a replacement for typed tools.** Read-only and typed tools (including
  ``list_expressions`` and the animation/rigging vocabulary) stay available so
  normal work can continue in restricted mode.

Adding a code-bearing tool
==========================

Add its name to :data:`CODE_BEARING_TOOLS` and call
:func:`arbitrary_script_refusal` at the start of its SDK function (which covers
both the ``main(**kwargs)`` dispatch path and direct SDK callers). The contract
test in ``tests/test_arbitrary_script_policy.py`` pins the inventory to the
shipped ``tools.yaml`` catalog so a new entry point cannot silently bypass it.
"""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_error

from dcc_mcp_maya._env import ENV_DISABLE_ARBITRARY_SCRIPT, resolve_arbitrary_script_disabled

#: Machine-readable scope label. Deliberately not ``global`` / ``sandbox``.
POLICY_SCOPE = "maya_adapter_tool_surface"

#: Canonical inventory of code-bearing tools in the Maya adapter. Sorted and
#: kept as a tuple so the contract test can pin it. ``get_script_node`` is
#: code-bearing only for ``action="create"`` (``get``/``delete`` are read-only
#: and destructive-but-not-code paths respectively).
#:
#: ``execute_python``, ``execute_mel`` and ``write_module`` predate this module;
#: they already honour the same flag through
#: :func:`dcc_mcp_maya._env.resolve_execute_python_disabled` /
#: ``resolve_execute_mel_disabled``. They are listed here so the policy has one
#: authoritative inventory and the contract test covers every entry point.
CODE_BEARING_TOOLS = (
    "create_expression",
    "edit_expression",
    "execute_mel",
    "execute_python",
    "get_script_node",
    "introspect_eval",
    "load_plugin",
    "reload_modules",
    "run_check",
    "run_entrypoint",
    "run_script",
    "start_debugpy",
    "write_module",
)


def arbitrary_script_refusal(tool_name: str) -> Optional[dict]:
    """Return a structured refusal when the policy blocks ``tool_name``.

    Returns ``None`` when the tool is not code-bearing or the flag is unset, so
    callers can write::

        refusal = arbitrary_script_refusal("create_expression")
        if refusal is not None:
            return refusal

    The decision is re-read from the environment on every call — no cached
    global state — so the flag takes effect as soon as it is set before Maya
    initialisation, which is the deployment the reporter described.
    """
    if tool_name not in CODE_BEARING_TOOLS or not resolve_arbitrary_script_disabled():
        return None
    return skill_error(
        "{} is disabled by operator policy".format(tool_name),
        "Unset {} to re-enable code-bearing tools in this Maya adapter. "
        "This flag is an adapter-local tool policy, not a host sandbox.".format(ENV_DISABLE_ARBITRARY_SCRIPT),
        possible_solutions=[
            "Use search_skills / dcc_capability_manifest -> load_skill -> typed tools instead.",
            "Read-only tools such as list_expressions remain available in restricted mode.",
            "Operators: review _code_policy.CODE_BEARING_TOOLS before adding new code-bearing tools.",
        ],
        tool_name=tool_name,
        policy_scope=POLICY_SCOPE,
    )
