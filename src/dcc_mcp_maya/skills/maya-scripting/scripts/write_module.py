"""Inject a Python module into Maya's interpreter for later import.

Same shape as PatrickPalmer/maya-mcp-server's ``write_module`` /
``create_module``: write a code string into a virtual module object,
register it in ``sys.modules`` under the chosen name, and let
subsequent ``execute_python`` calls do ``import <name>; <name>.run()``
without uploading the script on every call.

Why this exists
===============

``execute_python`` with a long inline ``code`` string forces the agent
to re-upload the entire script every time it wants to run a method.
The wire frame for the dispatch is small (JSON-line over qtserver),
but the AST parse on the Maya side still has to handle thousands of
characters per call and the agent's prompt budget pays for the
redundant upload.

The right shape is "upload the source once, call entry points many
times". ``write_module`` makes that possible without requiring the
script to live on the Maya host's filesystem.

Persistent across calls
=======================

The synthesised module is registered in ``sys.modules``. It survives
plug-in reload but **not** Maya process restart (Maya's interpreter
re-initialises ``sys.modules`` from scratch on every boot). Studios
that want truly persistent code should ship it as a real package on
``PYTHONPATH``.

The same name is overwritable when ``overwrite=True`` (the default).
Tests pin a workflow where ``write_module(name, source, overwrite=True)``
followed by ``execute_python(code='import name; name.run()')`` always
sees the latest source.

Safety
======

This is **arbitrary code injection**, gated by the same
``DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT`` env var that protects
``execute_python``. Operators who do not want agents synthesising
modules at runtime can set that to ``1``.
"""

from __future__ import annotations

import sys
import traceback
import types
from typing import Any, Dict, Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


def _validate_name(name: str) -> Optional[Dict[str, Any]]:
    """Reject empty / non-identifier-ish module names.

    We allow dotted names (``foo.bar``) so the agent can synthesise
    submodules, but each path component must be a valid Python
    identifier so ``import foo.bar`` actually works.
    """
    if not isinstance(name, str) or not name:
        return skill_error("Module name must be a non-empty string", "")
    for part in name.split("."):
        if not part.isidentifier():
            return skill_error(
                "Invalid module name component",
                "Each dotted segment of {0!r} must be a valid Python identifier.".format(name),
                possible_solutions=["Drop hyphens / leading digits / whitespace from the name."],
            )
    return None


def write_module(**params: Any):
    """Synthesise ``sys.modules[name]`` from a source string.

    Parameters
    ----------
    name:
        Dotted module name. Each path segment must be a valid Python
        identifier; the leaf is created as a fresh module unless it
        already exists and ``overwrite`` is true.
    source:
        Python source code. Compiled with ``filename = <write_module:name>``
        for friendlier tracebacks.
    overwrite:
        When ``True`` (default) re-executes ``source`` against the
        existing module's ``__dict__``, preserving the same module
        identity across rewrites (anything that imported the module
        previously keeps seeing the same object, with refreshed
        attributes). When ``False`` and the module already exists,
        the call is a no-op success — useful for "ensure-installed"
        idempotency.
    version:
        Optional opaque string stamped on the module as
        ``__dcc_mcp_module_version__``. Tests or follow-up calls can
        check it for cache invalidation without re-uploading source.
    """
    from dcc_mcp_maya._env import (  # noqa: PLC0415
        ENV_DISABLE_ARBITRARY_SCRIPT,
        ENV_DISABLE_EXECUTE_PYTHON,
        resolve_execute_python_disabled,
    )

    if resolve_execute_python_disabled():
        return skill_error(
            "write_module is disabled by operator policy",
            "Unset {0} or {1} to re-enable runtime module injection.".format(
                ENV_DISABLE_EXECUTE_PYTHON,
                ENV_DISABLE_ARBITRARY_SCRIPT,
            ),
        )

    name = params.get("name") or ""
    source = params.get("source") or params.get("code") or ""
    overwrite = bool(params.get("overwrite", True))
    version = str(params.get("version") or "")

    err = _validate_name(name)
    if err is not None:
        return err
    if not isinstance(source, str):
        return skill_error("`source` must be a string", "Got {0!r}".format(type(source).__name__))
    if not source.strip():
        return skill_error("`source` must be non-empty", "Pass the module body as `source`.")

    existing = sys.modules.get(name)

    if existing is not None and not overwrite:
        return skill_success(
            "Module already installed (overwrite=False)",
            prompt="Use overwrite=True to refresh the source.",
            installed=False,
            reused=True,
            name=name,
            version=getattr(existing, "__dcc_mcp_module_version__", ""),
        )

    filename = "<write_module:{0}>".format(name)
    try:
        compiled = compile(source, filename, "exec")
    except SyntaxError as exc:
        return skill_error(
            "Source has a SyntaxError",
            "{0}: {1}".format(type(exc).__name__, exc),
            traceback=traceback.format_exc(),
        )

    module = existing if existing is not None else types.ModuleType(name)
    module.__file__ = filename  # type: ignore[attr-defined]
    if version:
        module.__dcc_mcp_module_version__ = version  # type: ignore[attr-defined]

    try:
        exec(compiled, module.__dict__)  # noqa: S102 — this IS the injection point
    except BaseException as exc:  # noqa: BLE001 — relay to client envelope
        return skill_error(
            "Module body raised at import time",
            "{0}: {1}".format(type(exc).__name__, exc),
            traceback=traceback.format_exc(),
            name=name,
        )

    sys.modules[name] = module
    return skill_success(
        "Module installed",
        prompt="Now call execute_python with `import {0}; {0}.<entry>()` to invoke it.".format(name),
        installed=True,
        name=name,
        version=version,
        overwritten=existing is not None,
    )


@skill_entry
def main(**kwargs) -> dict:
    """Skill entry — delegates to :func:`write_module`."""
    return write_module(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
