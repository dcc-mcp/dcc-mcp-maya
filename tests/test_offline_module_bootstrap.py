"""Bootstrap must not import the lifecycle-only PEP 440 dependency."""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

OFFLINE_BOOTSTRAP = r"""
import importlib.util, json, os, pathlib, runpy, sys, types
assert importlib.util.find_spec('packaging') is None
assert importlib.util.find_spec('pip') is None
root = pathlib.Path(sys.argv[1]).resolve()
log_dir = root / 'smoke-bootstrap-logs'
os.environ['DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR'] = str(log_dir)
runtime_root = 'python37' if sys.version_info[:2] == (3, 7) else 'python'
sys.path.insert(0, str(root / runtime_root))
import dcc_mcp_core, dcc_mcp_maya
from dcc_mcp_maya import install
for module in (dcc_mcp_core, dcc_mcp_maya, install):
    assert str(pathlib.Path(module.__file__).resolve()).startswith(str(root))
assert not any(name == 'packaging' or name.startswith('packaging.') for name in sys.modules)
loaded = []
maya = types.ModuleType('maya')
cmds = types.ModuleType('maya.cmds')
cmds.evalDeferred = lambda callback, **kwargs: callback()
cmds.pluginInfo = lambda *args, **kwargs: bool(loaded)
cmds.loadPlugin = lambda name, **kwargs: loaded.append(name)
maya.cmds = cmds
sys.modules['maya'] = maya
sys.modules['maya.cmds'] = cmds
runpy.run_path(str(root / 'scripts' / 'userSetup.py'))
assert loaded == ['dcc_mcp_maya_plugin'], loaded
records = [json.loads(line) for path in log_dir.glob('*.jsonl') for line in path.read_text().splitlines()]
assert records and all(record.get('status') != 'failed' for record in records), records
assert not list((log_dir / 'pending').glob('*.json'))
assert not any(name == 'packaging' or name.startswith('packaging.') for name in sys.modules)
# Exercise the actual public serving entry point, including the PEP 440 guard.
# Only the licensed Maya host and network server are modeled; imports and the
# owning-thread dispatcher are the real bundled implementations.
import dcc_mcp_maya.headless as headless
from dcc_mcp_core.host import BlockingDispatcher
events = []
class Host:
    def __init__(self, dispatcher):
        assert isinstance(dispatcher, BlockingDispatcher)
    def is_background(self):
        return True
    def run_headless(self, stop_event=None):
        events.append('pump')
    def stop(self):
        events.append('host_stop')
class Server:
    def __init__(self, **kwargs):
        assert kwargs['instance_type'] == 'standalone'
    def register_builtin_actions(self, **kwargs):
        events.append('skills')
    def start(self):
        events.append('start')
    def stop(self):
        events.append('server_stop')
headless.MayaHost = Host
headless.MayaMcpServer = Server
dcc_mcp_maya.serve_headless()
assert events == ['skills', 'start', 'pump', 'server_stop', 'host_stop'], events
for version in ('0.19.63', '0.19.64rc1', '0.19.64.dev1'):
    events[:] = []
    headless.core_version = version
    try:
        dcc_mcp_maya.serve_headless()
    except RuntimeError as error:
        assert 'dcc-mcp-core>=0.19.64' in str(error)
    else:
        raise AssertionError('accepted unsupported Core ' + version)
    assert not events
for version in ('0.19.64', '0.19.64.post1', '0.19.64+local'):
    events[:] = []
    headless.core_version = version
    dcc_mcp_maya.serve_headless()
    assert events == ['skills', 'start', 'pump', 'server_stop', 'host_stop'], events
import packaging, packaging.version, packaging.specifiers
for module in (packaging, packaging.version, packaging.specifiers):
    assert pathlib.Path(module.__file__).resolve().relative_to(root / runtime_root)
assert packaging.__version__ == '24.0'
assert install._pep440_version('0.19.64rc1') < install._pep440_version('0.19.64')
assert install._pep440_version(dcc_mcp_core.__version__) in install._core_version_specifier()
assert importlib.util.find_spec('pip') is None
print(json.dumps({'headless': 'PASS (modeled host/server)', 'bootstrap': 'PASS', 'maya_origin': install.__file__, 'core_version': dcc_mcp_core.__version__, 'host': 'modeled; no licensed acceptance'}))
"""


def test_bootstrap_import_does_not_load_packaging():
    script = r"""
import importlib.abc, sys
sys.path.insert(0, sys.argv[1])
for name in list(sys.modules):
    if name == 'packaging' or name.startswith('packaging.'):
        del sys.modules[name]
class NoLifecycleDependencies(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'packaging' or fullname.startswith('packaging.'):
            raise AssertionError('bootstrap imported lifecycle dependency: ' + fullname)
sys.meta_path.insert(0, NoLifecycleDependencies())
import dcc_mcp_maya
from dcc_mcp_maya.install import bootstrap_user_setup
assert callable(bootstrap_user_setup)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(ROOT / "src")],
        capture_output=True,
        universal_newlines=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout)


@pytest.mark.packaging
@pytest.mark.parametrize("variant", ["portable", "pipeline"])
def test_actual_module_zip_bootstraps_without_site_or_pip(variant, tmp_path):
    """Run against sealed real ZIPs supplied by the release build gate."""
    location = os.environ.get("DCC_MCP_MAYA_TEST_MODULE_ZIPS")
    if not location:
        pytest.skip("requires real portable/pipeline ZIP outputs")
    payloads = list((Path(location) / variant).glob("*.zip"))
    assert len(payloads) == 1
    with zipfile.ZipFile(payloads[0]) as archive:
        archive.extractall(tmp_path)
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", OFFLINE_BOOTSTRAP, str(tmp_path / "dcc-mcp-maya")],
        capture_output=True,
        universal_newlines=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
