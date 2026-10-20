"""Cooperative headless host loop for real Maya HTTP tests."""

import pytest

from ._support import _ACTIVE_DISPATCHERS


@pytest.fixture(scope="session", autouse=True)
def standalone_host_loops():
    from dcc_mcp_maya import MayaMcpServer
    from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

    start = MayaMcpServer.start
    stop = MayaMcpServer.stop

    def tracked_start(server):
        handle = start(server)
        if isinstance(server._maya_dispatcher, MayaStandaloneDispatcher):
            _ACTIVE_DISPATCHERS[id(server)] = server._maya_dispatcher
        return handle

    def tracked_stop(server):
        try:
            return stop(server)
        finally:
            _ACTIVE_DISPATCHERS.pop(id(server), None)

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(MayaMcpServer, "start", tracked_start)
        patcher.setattr(MayaMcpServer, "stop", tracked_stop)
        yield
    _ACTIVE_DISPATCHERS.clear()
