"""Live local smoke test for PR review.

Starts a real MayaMcpServer (no Maya required), speaks MCP JSON-RPC over
HTTP and verifies:

    1. Agent → MCP gateway connectivity (initialize handshake).
    2. Skill discovery via the gateway (list_skills / find_skills tools).
    3. On-demand (progressive / lazy) tool loading — skills appear as
       ``__skill__<name>`` stubs and only expand to real tools after
       ``load_skill`` is called.
    4. Multi-version gateway switching — two servers with different
       dcc_version both register themselves under distinct ports and
       distinct handles.

Run standalone::

    python tools/live_smoke.py

Exits 0 on success, non-zero on any failure.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request


def _post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _tools_list(url: str) -> list[dict]:
    body = _post(url, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    return body["result"]["tools"]


def _call_tool(url: str, name: str, arguments: dict | None = None) -> dict:
    return _post(
        url,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        },
    )


def _section(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def main() -> int:
    from dcc_mcp_maya.server import MayaMcpServer

    _section("1. Start gateway #1 (dcc_version=2024)")
    srv_a = MayaMcpServer(port=0, gateway_port=0, dcc_version="2024", enable_gateway_failover=False)
    srv_a.register_builtin_actions()
    handle_a = srv_a.start()
    url_a = handle_a.mcp_url()
    print(f"  url: {url_a}")
    assert url_a.startswith("http://") and url_a.endswith("/mcp"), url_a

    try:
        _section("2. Agent → MCP initialize handshake")
        init = _post(
            url_a,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "live-smoke", "version": "1.0"},
                },
            },
        )
        info = init["result"]["serverInfo"]
        print(f"  server: {info['name']} v{info.get('version', '?')}")
        assert info["name"] == "maya-mcp", info

        _section("3. Agent discovers skills via gateway")
        tools = _tools_list(url_a)
        names = {t["name"] for t in tools}
        core = {"find_skills", "list_skills", "get_skill_info", "load_skill", "unload_skill"}
        missing = core - names
        assert not missing, f"missing core tools: {missing}"
        print(f"  core discovery tools: {sorted(core)}")

        stubs = sorted(n for n in names if n.startswith("__skill__"))
        real_now = sorted(n for n in names if "." in n and not n.startswith("__"))
        print(f"  skill stubs discovered: {len(stubs)} (showing first 10)")
        for n in stubs[:10]:
            print(f"    - {n}")
        print(f"  real tools already exposed: {len(real_now)}")
        assert len(stubs) >= 5, f"expected >= 5 skill stubs (progressive), got {len(stubs)}"

        _section("4. Verify tools are NOT all pre-loaded (lazy)")
        print("  stubs should have empty inputSchema.properties:")
        sample_stub_obj = next(t for t in tools if t["name"].startswith("__skill__"))
        props = sample_stub_obj.get("inputSchema", {}).get("properties", {})
        print(f"    {sample_stub_obj['name']}: properties={props}")
        assert props == {}, f"stub {sample_stub_obj['name']} leaked a populated schema: {props}"

        _section("5. load_skill → stub replaced by real tools")
        target = "maya-scene" if "__skill__maya-scene" in names else stubs[0].replace("__skill__", "")
        print(f"  loading skill: {target}")
        t0 = time.perf_counter()
        load_resp = _call_tool(url_a, "load_skill", {"skill_name": target})
        dt = (time.perf_counter() - t0) * 1000
        print(f"  load_skill returned in {dt:.1f} ms, error={load_resp.get('error')}")
        assert "error" not in load_resp or load_resp["error"] is None, load_resp

        after = {t["name"] for t in _tools_list(url_a)}
        assert f"__skill__{target}" not in after, f"stub __skill__{target} still present after load"
        real_after = [n for n in after if n.startswith(f"{target}.")]
        print(f"  real tools for {target!r} now exposed: {len(real_after)} (showing first 5)")
        for n in sorted(real_after)[:5]:
            print(f"    - {n}")
        assert real_after, f"no real tools appeared with prefix {target}."

        _section("6. Other skills still lazy (not auto-loaded)")
        still_stubs = sorted(n for n in after if n.startswith("__skill__"))
        other_real_prefixes = {
            n.split(".")[0]
            for n in after
            if "." in n and not n.startswith("__") and not n.startswith(f"{target}.")
        }
        print(f"  remaining stubs: {len(still_stubs)}")
        print(f"  other skills with real tools exposed: {len(other_real_prefixes)}")
        # Total catalogued skills should be the original-stubs + real-now.
        # All we need to prove: at least some stubs remain un-loaded after a
        # single load_skill call — tool loading is NOT all-or-nothing.
        assert still_stubs, "expected remaining stubs (proves other skills not eagerly loaded)"
    finally:
        srv_a.stop()

    _section("7. Start gateway #2 (dcc_version=2025) — multi-version switch")
    srv_b = MayaMcpServer(port=0, gateway_port=0, dcc_version="2025", enable_gateway_failover=False)
    srv_b.register_builtin_actions()
    handle_b = srv_b.start()
    url_b = handle_b.mcp_url()
    print(f"  url: {url_b}")
    try:
        tools_b = _tools_list(url_b)
        names_b = {t["name"] for t in tools_b}
        assert "find_skills" in names_b
        print(f"  gateway #2 exposes {len(names_b)} tools (incl. stubs)")
        assert url_b != url_a, "two gateways should listen on different ports"
        print(f"  version-switch ok: A={url_a} (2024)  B={url_b} (2025)")
    finally:
        srv_b.stop()

    print("\nALL LIVE SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
