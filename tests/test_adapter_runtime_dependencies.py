"""Audit the adapter's declared and imported runtime dependency boundary.

This is a source/metadata gate, not a universal stdlib detector or a sandbox for
user scripts. It never imports Maya or the adapter. The explicit stdlib inventory
is portable across our Python 3.7+ / OS matrix; a newly used module needs review.
Host modules are owned by Maya and its plugins, never bundled from PyPI. Existing
optional integrations are allowed only in named functions with missing-import
handlers. Arbitrary user-module inspection is separately audited below.

Build requirements, developer tooling, and test imports are intentionally outside
the runtime boundary. See AGENTS.md, "Adapter Runtime Dependency Boundary".
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.7-3.10 test environments
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "src/dcc_mcp_maya/"
FIRST_PARTY_DISTRIBUTIONS = {"dcc-mcp-core", "dcc-mcp-server"}
FIRST_PARTY_MODULES = {"dcc_mcp_maya", "dcc_mcp_core", "dcc_mcp_server"}
HOST_MODULES = {"maya", "mtoa", "pxr", "PySide", "PySide2", "PySide6", "shiboken", "shiboken2", "shiboken6"}

# Audited imports in src/ and the shipped Maya entrypoints, not sys.stdlib_module_names
# (unavailable on older CI Pythons and not an assertion of Maya compatibility).
STDLIB_MODULES = set(
    "__future__ __main__ argparse ast atexit base64 binascii collections concurrent "
    "contextlib copy ctypes dataclasses datetime difflib email faulthandler functools "
    "glob hashlib importlib inspect io json keyword logging math numbers os pathlib queue re "
    "runpy shutil signal socket stat statistics subprocess sys tempfile threading "
    "time traceback types typing urllib uuid weakref webbrowser zipfile".split()
)

# (source, function, exact import) -> justification. No blanket optional-module allowlist.
OPTIONAL_IMPORTS = {
    (PACKAGE + "_dev_session.py", "_debugpy_status", "debugpy"): "Explicit developer debugger status only",
    (PACKAGE + "_dev_session.py", "start_debugpy", "debugpy"): "Explicit developer debugger attach only",
    (PACKAGE + "_affinity.py", "_default_yaml_loader", "yaml"): "Missing PyYAML keeps safe main-thread affinity",
    (
        PACKAGE + "_version_check.py",
        "_metadata_module",
        "importlib_metadata",
    ): "Missing backport uses stdlib metadata scan",
}

# Nonliteral import expressions require individual review. Fixed host candidates
# are checked separately below; user-selected project modules are not adapter deps.
DYNAMIC_IMPORTS = {
    (PACKAGE + "_dev_session.py", "_resolve_callable"): ("module_name",),  # User-selected project callable
    (PACKAGE + "_dev_session.py", "_qt_modules"): (
        'qt_name + ".QtWidgets"',
        'qt_name + ".QtCore"',
        "shiboken_name",
    ),
    (PACKAGE + "_recovery_dialog.py", "_import_qt_widgets"): ("module_name",),
    (PACKAGE + "_resources.py", "_maya_api_signatures_producer"): ("module_path",),
    (PACKAGE + "render_setup.py", "load_render_setup"): ("RENDER_SETUP_MODULE",),
    (PACKAGE + "skills/maya-scripting/scripts/introspect.py", "_inspect_openmaya"): (
        '".".join(parts[:-1])',
    ),  # User-requested introspection
    (PACKAGE + "skills/maya-scripting/scripts/introspect.py", "_get_module_names"): ("module",),
    ("maya/plugin/dcc_mcp_maya_plugin.py", "_set_clipboard_text"): ("binding",),
    ("maya/userSetup.py", "_package_version"): ("module_name",),  # Best-effort first-party provenance
}

# Verify actual declarations behind fixed dynamic imports, not just their variable names.
HOST_IMPORT_TARGETS = (
    (
        PACKAGE + "_dev_session.py",
        "_qt_modules",
        "candidates",
        (("PySide6", "shiboken6"), ("PySide2", "shiboken2"), ("PySide", "shiboken")),
    ),
    (
        PACKAGE + "_recovery_dialog.py",
        "_import_qt_widgets",
        "module_name",
        ("PySide6.QtWidgets", "PySide2.QtWidgets", "PySide.QtGui"),
    ),
    (
        PACKAGE + "_resources.py",
        "_maya_api_signatures_producer",
        "module_path",
        ("maya.api.OpenMaya", "maya.api.OpenMayaAnim", "maya.api.OpenMayaUI", "maya.OpenMaya"),
    ),
    (PACKAGE + "render_setup.py", "<module>", "RENDER_SETUP_MODULE", "maya.app.renderSetup.model.renderSetup"),
    ("maya/plugin/dcc_mcp_maya_plugin.py", "_set_clipboard_text", "binding", ("PySide2", "PySide6")),
)


def _runtime_sources():
    return sorted(set((ROOT / "src").rglob("*.py")) | set((ROOT / "maya").rglob("*.py")) | {ROOT / "maya_bootstrap.py"})


def _walk(node, parents=()):
    yield node, parents
    for child in ast.iter_child_nodes(node):
        yield from _walk(child, parents + (node,))


def _scope(parents):
    names = [node.name for node in parents if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    return ".".join(names) or "<module>"


def _expression(source):
    return ast.dump(ast.parse(source, mode="eval").body)


def _has_missing_import_handler(parents):
    """A try at definition time cannot protect an import executed by a function."""
    child = None
    for parent in reversed(parents):
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        if isinstance(parent, ast.Try) and child in parent.body:
            for handler in parent.handlers:
                names = (
                    {node.id for node in ast.walk(handler.type) if isinstance(node, ast.Name)}
                    if handler.type
                    else set()
                )
                if names & {"ImportError", "ModuleNotFoundError"} and not any(
                    isinstance(node, ast.Raise) for statement in handler.body for node in ast.walk(statement)
                ):
                    return True
        child = parent
    return False


def _dependency_violations(project):
    errors = []
    if set(project.get("dynamic", ())) & {"dependencies", "optional-dependencies"}:
        errors.append("Runtime dependencies must be statically declared for audit")
    groups = {"dependencies": project.get("dependencies", [])}
    groups.update(
        {"extra " + name: items for name, items in project.get("optional-dependencies", {}).items() if name != "dev"}
    )
    for group, dependencies in groups.items():
        for declaration in dependencies:
            requirement = Requirement(declaration)
            if (
                canonicalize_name(requirement.name) not in FIRST_PARTY_DISTRIBUTIONS
                or requirement.extras
                or requirement.url
            ):
                errors.append("{}: {} is not an approved first-party runtime requirement".format(group, declaration))
    return errors


def _import_violations(source, path):
    tree = ast.parse(source, filename=path)
    importlib_names = {"importlib"}
    importer_names = {"__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            importlib_names.update(alias.asname or alias.name for alias in node.names if alias.name == "importlib")
        elif isinstance(node, ast.ImportFrom) and node.module in {"importlib", "builtins"} and not node.level:
            importer_names.update(
                alias.asname or alias.name for alias in node.names if alias.name in {"import_module", "__import__"}
            )

    errors = []

    def check(module, node, parents):
        if module.startswith(".") or module.split(".")[0] in STDLIB_MODULES | HOST_MODULES | FIRST_PARTY_MODULES:
            return
        key = (path, _scope(parents), module)
        if key in OPTIONAL_IMPORTS and _has_missing_import_handler(parents + (node,)):
            return
        errors.append("{}:{}: unapproved runtime import {}".format(path, node.lineno, module))

    for node, parents in _walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                check(alias.name, node, parents)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            check(node.module or "", node, parents)
        elif isinstance(node, ast.Call):
            func = node.func
            is_import = isinstance(func, ast.Name) and func.id in importer_names
            is_import = is_import or (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id in importlib_names
                and func.attr == "import_module"
            )
            if not is_import:
                continue
            arg = node.args[0] if node.args else next((kw.value for kw in node.keywords if kw.arg == "name"), None)
            try:
                literal = ast.literal_eval(arg) if arg is not None else None
            except (ValueError, TypeError):
                literal = None
            if isinstance(literal, str):
                check(literal, node, parents)
            elif arg is None or ast.dump(arg) not in {
                _expression(expression) for expression in DYNAMIC_IMPORTS.get((path, _scope(parents)), ())
            }:
                errors.append("{}:{}: unaudited dynamic import".format(path, node.lineno))
    return errors


class TestAdapterRuntimeDependencies(unittest.TestCase):
    def test_declared_runtime_dependencies_are_first_party_only(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(_dependency_violations(project), [])

    def test_declaration_guard_rejects_runtime_and_runtime_extra_dependencies(self):
        for dependency in (
            "packaging>=21.3",
            "PySide6",
            "requests; python_version < '3.8'",
            "dcc-mcp-core[dev]>=0.20",
            "dcc-mcp-server @ https://example.invalid/server.whl",
        ):
            for project in ({"dependencies": [dependency]}, {"optional-dependencies": {"runtime": [dependency]}}):
                with self.subTest(project=project):
                    self.assertTrue(_dependency_violations(project))
        self.assertTrue(_dependency_violations({"dynamic": ["dependencies"]}))
        self.assertEqual(
            _dependency_violations({"optional-dependencies": {"dev": ["packaging", "pytest", "ruff"]}}), []
        )
        self.assertEqual(_dependency_violations({"dependencies": ["DCC_MCP.Core>=0.20", "dcc-mcp-server>=0.18"]}), [])

    def test_all_runtime_sources_have_audited_imports(self):
        sources = _runtime_sources()
        self.assertTrue(any("/skills/" in path.as_posix() for path in sources))
        for path in sources:
            with self.subTest(source=path.relative_to(ROOT).as_posix()):
                self.assertEqual(
                    _import_violations(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix()), []
                )

    def test_import_guard_rejects_undeclared_and_lazy_third_party_imports(self):
        for source in (
            "import packaging.version",
            "from requests import get",
            "def action():\n import yaml",
            "try:\n import debugpy\nexcept ImportError:\n pass",
            "__import__('packaging')",
            "import importlib as loader\nloader.import_module('requests')",
            "from importlib import import_module as load\nload(name='packaging')",
            "import importlib\nimportlib.import_module(module_name)",
        ):
            with self.subTest(source=source):
                self.assertTrue(_import_violations(source, PACKAGE + "new_module.py"))

    def test_import_guard_allows_stdlib_first_party_host_and_relative_imports(self):
        source = "import os, keyword, maya.cmds, PySide2, shiboken6, pxr, mtoa\nfrom dcc_mcp_core import skill\nfrom . import helper\n__import__('dcc_mcp_server')"
        self.assertEqual(_import_violations(source, PACKAGE + "new_module.py"), [])

    def test_optional_imports_must_remain_lazy_scoped_and_failure_tolerant(self):
        path = PACKAGE + "_dev_session.py"
        good = "def start_debugpy():\n try:\n  import debugpy\n except ImportError:\n  return None"
        self.assertEqual(_import_violations(good, path), [])
        for source in (
            "import debugpy",
            "def start_debugpy():\n import debugpy",
            good.replace("return None", "raise"),
            good.replace("ImportError", "ValueError"),
            "try:\n def start_debugpy():\n  import debugpy\nexcept ImportError:\n pass",
        ):
            with self.subTest(source=source):
                self.assertTrue(_import_violations(source, path))

    def test_fixed_dynamic_import_targets_remain_host_owned(self):
        for path, scope, variable, expected in HOST_IMPORT_TARGETS:
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
            values = []
            for node, parents in _walk(tree):
                if _scope(parents) != scope:
                    continue
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == variable for target in node.targets
                ):
                    values.append(ast.literal_eval(node.value))
                elif isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == variable:
                    values.append(ast.literal_eval(node.iter))
            with self.subTest(path=path, variable=variable):
                self.assertEqual(values, [expected])


if __name__ == "__main__":
    unittest.main()
