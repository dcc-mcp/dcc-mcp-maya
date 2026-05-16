"""Wire-format entry point for the ``dcc-mcp-server sidecar`` binary.

The sidecar binary (RFC #998 Phase 2) reaches Maya by sending a single
Python expression over the host's ``commandPort``::

    __import__('dcc_mcp_maya._sidecar', fromlist=['dispatch']).dispatch(
        {"action": ..., "args": ..., "request_id": ...}
    )

That import path is **pinned** in the Rust client (see
``dcc-mcp-host-rpc`` ``commandport.rs``) so we must keep the module
name and ``dispatch`` symbol exactly as the binary expects. This file
is intentionally a one-line shim — the real implementation lives in
:mod:`dcc_mcp_maya.sidecar._dispatcher` alongside the rest of the
sidecar support code.

Skill authors should never import this module directly. The leading
underscore is the canonical "internal API" marker.
"""

from __future__ import annotations

from dcc_mcp_maya.sidecar._dispatcher import dispatch, dispatch_payload

__all__ = ["dispatch", "dispatch_payload"]
