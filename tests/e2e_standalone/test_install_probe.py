"""Check install preflight in a fresh, real mayapy child process."""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.e2e


def test_install_probe_in_fresh_mayapy():
    pytest.importorskip("maya.standalone", reason="requires an installed Maya / mayapy")
    from dcc_mcp_maya import install

    # Do not initialize Maya in this process or patch the child probe. The
    # installed interpreter must bootstrap and clean up its own standalone.
    metadata = install._probe_target(sys.executable)

    assert install.MIN_MAYA_VERSION <= int(metadata["maya_version"].split(".")[0]) <= install.MAX_MAYA_VERSION
    assert metadata["python_version"] == ".".join(map(str, sys.version_info[:3]))
    assert metadata["adapter_version"] == install.__version__
    assert metadata["core_version"] == install.dcc_mcp_core.__version__
