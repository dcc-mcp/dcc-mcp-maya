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
import importlib.util, json, pathlib, runpy, sys, types
root = pathlib.Path(sys.argv[1]).resolve()
runtime_root = 'python37' if sys.version_info[:2] == (3, 7) else 'python'
sys.path.insert(0, str(root / runtime_root))
assert importlib.util.find_spec('packaging') is None
assert importlib.util.find_spec('pip') is None
import dcc_mcp_core, dcc_mcp_maya
from dcc_mcp_maya import install
for module in (dcc_mcp_core, dcc_mcp_maya, install):
    assert str(pathlib.Path(module.__file__).resolve()).startswith(str(root))
assert not any(name == 'packaging' or name.startswith('packaging.') for name in sys.modules)
loaded = []
maya = types.ModuleType('maya')
cmds = types.ModuleType('maya.cmds')
cmds.evalDeferred = lambda callback, **kwargs: callback()
cmds.pluginInfo = lambda *args, **kwargs: False
cmds.loadPlugin = lambda name, **kwargs: loaded.append(name)
maya.cmds = cmds
sys.modules['maya'] = maya
sys.modules['maya.cmds'] = cmds
runpy.run_path(str(root / 'scripts' / 'userSetup.py'))
assert loaded == ['dcc_mcp_maya_plugin'], loaded
assert not any(name == 'packaging' or name.startswith('packaging.') for name in sys.modules)
print(json.dumps({'bootstrap': 'PASS', 'maya_origin': install.__file__, 'core_version': dcc_mcp_core.__version__, 'host': 'modeled; no licensed acceptance'}))
"""


def test_bootstrap_import_does_not_load_packaging():
    script = r"""
import importlib.abc, sys
sys.path.insert(0, sys.argv[1])
import dcc_mcp_maya
for name in list(sys.modules):
    if name == 'packaging' or name.startswith('packaging.'):
        del sys.modules[name]
class NoLifecycleDependencies(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'packaging' or fullname.startswith('packaging.'):
            raise AssertionError('bootstrap imported lifecycle dependency: ' + fullname)
sys.meta_path.insert(0, NoLifecycleDependencies())
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
