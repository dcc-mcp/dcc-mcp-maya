"""Execute the install probe in real subprocesses with controlled Maya modules.

These are lifecycle regression tests, not real Maya / licensing acceptance.
The fake command module deliberately has no ``about`` until initialization.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import textwrap

import pytest

from dcc_mcp_maya import install


@pytest.fixture
def probe_runtime(tmp_path, monkeypatch):
    modules = tmp_path / "probe modules"
    maya = modules / "maya"
    maya.mkdir(parents=True)
    events = tmp_path / "events.jsonl"
    (maya / "__init__.py").write_text("", encoding="utf-8")
    (maya / "cmds.py").write_text("# Bare mayapy exposes an unpopulated command module.\n", encoding="utf-8")
    (maya / "standalone.py").write_text(
        textwrap.dedent(
            """\
            import json
            import os
            import time
            from maya import cmds

            def record(event):
                with open(os.environ['PROBE_EVENTS'], 'a') as stream:
                    stream.write(json.dumps(event) + '\\n')

            def about(version=False):
                record('about')
                assert version is True
                if os.environ.get('PROBE_QUERY_ERROR'):
                    raise RuntimeError('version query failed')
                return '2026'

            def initialize(name='python'):
                record('initialize')
                assert name == 'python'
                if callable(getattr(cmds, 'about', None)):
                    raise RuntimeError('Maya is already initialized')
                if os.environ.get('PROBE_INIT_ERROR'):
                    raise RuntimeError('standalone initialization failed')
                if os.environ.get('PROBE_INIT_DELAY'):
                    time.sleep(60)
                cmds.about = about
                print('Maya startup chatter')

            def uninitialize():
                record('uninitialize')
                del cmds.about
                print('Maya shutdown chatter')
                if os.environ.get('PROBE_CLEANUP_ERROR'):
                    raise RuntimeError('standalone cleanup failed')
            """
        ),
        encoding="utf-8",
    )
    for module, version in (("dcc_mcp_core", install.MIN_CORE_VERSION), ("dcc_mcp_maya", install.__version__)):
        (modules / (module + ".py")).write_text(
            "from maya.standalone import record\nrecord(%r)\n__version__ = %r\n" % (module, version),
            encoding="utf-8",
        )
    monkeypatch.setenv("PYTHONPATH", str(modules))
    monkeypatch.setenv("PROBE_EVENTS", str(events))

    def read_events():
        if not events.exists():
            return []
        return [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]

    return modules, read_events


@pytest.mark.parametrize("uninitialized_cmds", ["", "about = None\n"])
def test_probe_initializes_bare_mayapy_and_emits_metadata_after_cleanup(probe_runtime, uninitialized_cmds):
    modules, events = probe_runtime
    (modules / "maya" / "cmds.py").write_text(uninitialized_cmds, encoding="utf-8")

    assert install._probe_target(sys.executable) == {
        "maya_version": "2026",
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "core_version": install.MIN_CORE_VERSION,
        "adapter_version": install.__version__,
    }
    assert events() == ["initialize", "dcc_mcp_core", "dcc_mcp_maya", "about", "uninitialize"]


def test_probe_preserves_a_runtime_initialized_by_sitecustomize(probe_runtime):
    modules, events = probe_runtime
    (modules / "sitecustomize.py").write_text(
        "from maya import cmds, standalone\ncmds.about = standalone.about\n", encoding="utf-8"
    )

    assert install._probe_target(sys.executable)["maya_version"] == "2026"
    assert "initialize" not in events()
    assert "uninitialize" not in events()


def test_probe_does_not_teardown_preinitialized_runtime_on_query_failure(probe_runtime, monkeypatch):
    modules, events = probe_runtime
    (modules / "sitecustomize.py").write_text(
        "from maya import cmds, standalone\ncmds.about = standalone.about\n", encoding="utf-8"
    )
    monkeypatch.setenv("PROBE_QUERY_ERROR", "1")

    with pytest.raises(install.LifecycleError, match="version query failed"):
        install._probe_target(sys.executable)

    assert "initialize" not in events()
    assert "uninitialize" not in events()


@pytest.mark.parametrize("module", ["dcc_mcp_core", "dcc_mcp_maya"])
def test_probe_cleans_up_after_dependency_import_failure(probe_runtime, module):
    modules, events = probe_runtime
    (modules / (module + ".py")).write_text("raise ImportError('dependency failed')\n", encoding="utf-8")

    with pytest.raises(install.LifecycleError, match="dependency failed") as caught:
        install._probe_target(sys.executable)

    assert caught.value.exit_code == install.INSTALL_EXIT_PREFLIGHT
    assert caught.value.stage == "python"
    assert caught.value.reason == "target_import_failed"
    assert events()[0] == "initialize"
    assert events()[-1] == "uninitialize"


@pytest.mark.parametrize(
    "failure, diagnostic, teardown",
    [
        ("PROBE_INIT_ERROR", "standalone initialization failed", False),
        ("PROBE_QUERY_ERROR", "version query failed", True),
        ("PROBE_CLEANUP_ERROR", "standalone cleanup failed", True),
    ],
)
def test_probe_does_not_hide_lifecycle_failures(probe_runtime, monkeypatch, failure, diagnostic, teardown):
    _modules, events = probe_runtime
    monkeypatch.setenv(failure, "1")

    with pytest.raises(install.LifecycleError, match=diagnostic) as caught:
        install._probe_target(sys.executable)

    assert caught.value.reason == "target_import_failed"
    assert events().count("uninitialize") == int(teardown)


def test_probe_preserves_query_failure_when_cleanup_also_fails(probe_runtime, monkeypatch):
    monkeypatch.setenv("PROBE_QUERY_ERROR", "1")
    monkeypatch.setenv("PROBE_CLEANUP_ERROR", "1")

    with pytest.raises(install.LifecycleError, match="version query failed") as caught:
        install._probe_target(sys.executable)

    assert "standalone cleanup failed" in str(caught.value)


def test_probe_timeout_is_bounded_and_classified(probe_runtime, monkeypatch):
    _modules, events = probe_runtime
    monkeypatch.setenv("PROBE_INIT_DELAY", "1")
    run = subprocess.run

    def run_with_short_timeout(*args, **kwargs):
        assert kwargs["timeout"] == 20
        kwargs["timeout"] = 0.5
        return run(*args, **kwargs)

    monkeypatch.setattr(install.subprocess, "run", run_with_short_timeout)
    with pytest.raises(install.LifecycleError) as caught:
        install._probe_target(sys.executable)

    assert caught.value.exit_code == install.INSTALL_EXIT_PREFLIGHT
    assert caught.value.reason == "python_probe_failed"
    assert isinstance(caught.value.__cause__, subprocess.TimeoutExpired)
    # The child never claims cleanup completed after it was forcibly stopped.
    assert events() == ["initialize"]


def test_probe_script_retains_python37_syntax(probe_runtime, monkeypatch):
    run = subprocess.run

    def check_script(command, **kwargs):
        if sys.version_info >= (3, 8):
            ast.parse(command[2], feature_version=7)
        return run(command, **kwargs)

    monkeypatch.setattr(install.subprocess, "run", check_script)
    assert install._probe_target(sys.executable)["maya_version"] == "2026"


def test_install_dry_run_uses_real_probe_without_writing_receipt(probe_runtime, tmp_path, monkeypatch, capsys):
    maya_root = tmp_path / "Maya2026"
    maya_root.mkdir()
    profile = tmp_path / "profile"
    receipt = tmp_path / "receipt.json"
    monkeypatch.setenv("DCC_MCP_MAYA_MODULES_DIR", str(profile / "modules"))
    monkeypatch.setenv("DCC_MCP_MAYA_SCRIPTS_DIR", str(profile / "scripts"))
    monkeypatch.setenv("DCC_MCP_MAYA_RECEIPT", str(receipt))

    code = install.main(["install", "--json", "--dry-run", "--dcc-path", str(maya_root), "--python", sys.executable])

    report = json.loads(capsys.readouterr().out)
    assert code == install.INSTALL_EXIT_OK
    assert report["status"] == "planned"
    assert report["host"]["version"] == "2026"
    assert not profile.exists()
    assert not receipt.exists()
