"""Fixtures for docker_maya and instance_factory modules.

Provides shared pytest fixtures for Docker and local instance testing.
"""

import pytest


@pytest.fixture
def docker_registry():
    """Fixture providing Docker registry URL (empty string for Docker Hub)."""
    return ""


@pytest.fixture
def gateway_port():
    """Fixture providing default gateway port."""
    return 9765
