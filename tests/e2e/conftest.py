"""E2E test configuration.

Requires a real mayapy interpreter (tahv/mayapy Docker image).
All tests in ``tests/e2e/`` are skipped automatically when ``maya.standalone``
is not importable, so the suite is safe to collect under normal pytest runs.

Run locally::

    mayapy -m pytest tests/e2e/ -v

CI::

    docker run --rm -v $(pwd):/workspace -w /workspace \\
        tahv/mayapy:2025 \\
        mayapy -m pytest tests/e2e/ -v
"""

# Import future modules
from __future__ import annotations

# Import third-party modules
import pytest


def pytest_configure(config):
    """Register the ``e2e`` marker."""
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end tests that require a real Maya standalone interpreter (tahv/mayapy)",
    )


def pytest_collection_modifyitems(items, config):
    """Skip all e2e tests when maya.standalone is not available."""
    try:
        import maya.standalone  # noqa: F401
    except ImportError:
        skip_marker = pytest.mark.skip(reason="maya.standalone not available — run under mayapy")
        for item in items:
            if "e2e" in item.nodeid:
                item.add_marker(skip_marker)
