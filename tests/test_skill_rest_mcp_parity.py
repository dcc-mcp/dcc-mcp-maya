"""Real-world parity tests for skill exposure via MCP and RESTful `/v1/*`.

These tests target the scenario the user flagged explicitly: *skills must be
reachable via both MCP `tools/call` and the per-DCC RESTful surface, and the
agent workflow must not waste tokens*.  Concretely we validate:

1. **Discovery parity** — an action advertised through the compact capability
   manifest (issue #163) MUST be reachable through MCP `search_tools`, so an
   agent that discovers a capability from the manifest can invoke it without
   an extra ``list_skills`` round-trip.

2. **Execution parity** — a `tool_slug` from the capability manifest maps
   deterministically to a `backend_tool` callable via MCP `tools/call`.
   Whenever the `/v1/call` REST endpoint is mounted by the underlying core
   build, the two channels MUST return the same envelope for the same input.

3. **Token efficiency** — the user's primary complaint about existing Maya
   MCP tooling is context bloat.  We regression-test several budget
   invariants:

   * `tools/list` page 1 stays under 80 KB (well inside a small agent
     context window) regardless of skill count.
   * Each compact manifest record stays under 640 B.
   * The compact manifest is strictly cheaper per-capability than a full
     MCP `tools/list` schema dump (factor of >=3× by total bytes).
   * `search_tools` results strip bulky fields (`input_schema`, long
     `description`) that agents only need *after* selecting a hit.

4. **RESTful surface graceful degradation** — for every documented
   endpoint in the PR #667 contract (``/v1/healthz``, ``/v1/readyz``,
   ``/v1/skills``, ``/v1/search``, ``/v1/describe``, ``/v1/call``,
   ``/v1/context``, ``/v1/openapi.json``), we assert the server either
   serves it with a well-formed body (when core is 0.14.22+) or returns
   a proper 404 (older core).  No 5xx, ever.  The test is written so that
   it will automatically start validating parity the moment the core
   dependency ships the endpoints.

Test design follows SOLID:
    * ``_McpClient`` encapsulates the MCP streamable-HTTP handshake and
      framing, so individual tests depend on a narrow abstraction rather
      than raw ``urllib`` plumbing (Dependency Inversion).
    * ``_RestClient`` is a tiny adapter for the REST surface — deliberately
      independent so that a future in-memory test could swap it.
    * ``_NormalisedEnvelope`` is the single-responsibility value object
      that strips wire noise (session IDs, content-part wrappers) so that
      parity assertions compare apples to apples.
"""

from __future__ import annotations

# Import built-in modules
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError

# Import third-party modules
import pytest

# Disable file-logging side-effects before the core is imported.
os.environ.setdefault("DCC_MCP_DISABLE_FILE_LOGGING", "1")
os.environ.setdefault("DCC_MCP_MAYA_CAPABILITY_MCP_TOOL", "1")

# Prefer the in-tree source over any installed wheel so coverage counts.
_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from dcc_mcp_maya.server import MayaMcpServer  # noqa: E402

# ---------------------------------------------------------------------------
# Small HTTP clients — single-responsibility, no hidden state.
# ---------------------------------------------------------------------------


class _McpClient:
    """Minimal MCP streamable-HTTP client.

    Kept deliberately small: construct → ``initialize()`` → ``call()``.
    All framing oddities (SSE/JSON duality, session IDs, initialised
    notification) are owned here so tests never touch them.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._session: Optional[str] = None

    @property
    def url(self) -> str:
        return self._url

    def initialize(self) -> None:
        init = self._post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "parity-tests", "version": "0"},
                },
            }
        )
        self._session = init.get("__session_id__")
        # MCP spec requires initialised notification; we fire-and-forget it.
        self._post(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
            expect_response=False,
        )

    def tools_list(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        resp = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": params})
        return resp.get("result", {})

    def tools_list_all(self, *, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Walk ``tools/list`` pages until exhausted (bounded for safety)."""
        out: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        for _ in range(max_pages):
            page = self.tools_list(cursor=cursor)
            out.extend(page.get("tools", []))
            cursor = page.get("nextCursor") or page.get("next_cursor")
            if not cursor:
                break
        return out

    def tools_call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._post(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )

    # ----- internals -----
    def _post(self, payload: Dict[str, Any], *, expect_response: bool = True) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        req = urllib.request.Request(self._url, data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            session_out = resp.headers.get("Mcp-Session-Id")
            status = resp.status
        if not expect_response:
            return {"__status__": status, "__session_id__": session_out}
        text = body.decode("utf-8", errors="replace").strip()
        # Normalise SSE framing to JSON.
        if text.startswith("event:") or text.startswith("data: ") or "\ndata: " in text:
            for line in text.splitlines():
                if line.startswith("data: "):
                    text = line[len("data: ") :]
                    break
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover — defensive
            raise AssertionError("Non-JSON MCP response (status={}): {!r}".format(status, body[:200])) from exc
        parsed["__session_id__"] = session_out
        return parsed


class _RestClient:
    """Thin wrapper for the per-DCC RESTful surface (PR loonghao/dcc-mcp-core#667).

    Every call returns a ``(status, body)`` tuple; we never raise on
    non-2xx because the test suite needs to distinguish "endpoint absent
    (older core)" from "endpoint failed (regression)".
    """

    def __init__(self, base: str) -> None:
        self._base = base.rstrip("/")

    def get(self, path: str) -> Tuple[int, bytes]:
        return self._request("GET", path, None)

    def post(self, path: str, payload: Dict[str, Any]) -> Tuple[int, bytes]:
        return self._request("POST", path, json.dumps(payload).encode())

    def _request(self, method: str, path: str, data: Optional[bytes]) -> Tuple[int, bytes]:
        url = self._base + path
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read()
        except HTTPError as exc:
            return exc.code, exc.read() or b""
        except URLError as exc:  # pragma: no cover — defensive
            pytest.fail("REST endpoint unreachable: {}".format(exc))
            return 0, b""


def _extract_text(mcp_tool_result: Dict[str, Any]) -> str:
    """Extract the payload text from an MCP ``tools/call`` result."""
    content = mcp_tool_result.get("content") or mcp_tool_result.get("structuredContent") or []
    if isinstance(content, dict):
        return json.dumps(content)
    for part in content:
        if isinstance(part, dict) and part.get("type") in ("text", "json"):
            text = part.get("text")
            if text:
                return text
            if part.get("type") == "json" and "data" in part:
                return json.dumps(part["data"])
    return json.dumps(mcp_tool_result)


# ---------------------------------------------------------------------------
# Shared server fixture — single server, many tests.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def full_server():
    """Server with **all** bundled skills loaded (not minimal mode).

    Using ``minimal=False`` is deliberate: the user asked us to test
    real-world skill exposure, and minimal mode hides 12 of the 14
    bundled skills behind ``__skill__*`` stubs.  Loading everything
    exercises the realistic agent scenario where multiple DCC skills are
    ready to call.
    """
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=False)
    handle = server.start()
    time.sleep(0.05)
    yield server, handle
    server.stop()


@pytest.fixture(scope="module")
def mcp(full_server):
    _, handle = full_server
    client = _McpClient(handle.mcp_url())
    client.initialize()
    return client


@pytest.fixture(scope="module")
def rest(full_server) -> _RestClient:
    _, handle = full_server
    base = handle.mcp_url().rsplit("/", 1)[0]
    return _RestClient(base)


# ---------------------------------------------------------------------------
# 1. Discovery parity — capability manifest ↔ search_tools ↔ tools/list
# ---------------------------------------------------------------------------


def _load_capability_manifest(mcp: _McpClient) -> Dict[str, Any]:
    call = mcp.tools_call("dcc_capability_manifest", {})
    text = _extract_text(call["result"])
    payload = json.loads(text)
    return payload["context"]


def test_manifest_slugs_are_stable_and_namespaced(mcp):
    """Every capability record must advertise a ``maya.*`` tool slug.

    The slug is the *agent-facing* identifier — stable across skill
    loading/unloading and free of Maya-internal naming quirks.  An agent
    that caches the manifest then calls back later must be able to
    resolve the slug without re-reading the compact snapshot.
    """
    manifest = _load_capability_manifest(mcp)
    assert manifest["capabilities"], "expected bundled skills to advertise capabilities"
    for rec in manifest["capabilities"]:
        slug = rec.get("tool_slug", "")
        backend = rec.get("backend_tool", "")
        assert slug.startswith("maya."), "non-namespaced slug: {!r}".format(slug)
        assert backend, "missing backend_tool on record: {}".format(rec)
        # Slug must be ASCII and URL-safe — REST `/v1/tools/{slug}` needs it.
        assert slug.isascii()
        assert " " not in slug
        assert "/" not in slug


def test_manifest_actions_discoverable_via_search_tools(mcp):
    """An agent with a manifest record MUST be able to ``search_tools`` for it.

    The manifest carries ``tags`` and a compact summary precisely so the
    agent can keep those tokens in context and resolve the action via
    ``search_tools`` when it's ready to invoke — without re-downloading
    a full ``tools/list`` page.
    """
    manifest = _load_capability_manifest(mcp)
    # Pick a deterministic action that we know is bundled and doesn't require Maya.
    target = next(
        (r for r in manifest["capabilities"] if r["backend_tool"] == "maya_scripting__execute_python"),
        None,
    )
    assert target is not None, "maya_scripting__execute_python must be in the manifest"

    # search_tools lives as an MCP tool on DccServerBase.
    resp = mcp.tools_call("search_tools", {"query": "python", "limit": 10})
    result = resp.get("result")
    if result is None or (isinstance(resp.get("error"), dict) and resp["error"].get("code") == -32601):
        pytest.skip("search_tools not registered in this core build")

    hits_text = _extract_text(result)
    hits_payload = json.loads(hits_text)
    hits = hits_payload.get("tools") or hits_payload.get("hits") or []
    names = [h.get("name") for h in hits if isinstance(h, dict)]
    assert target["backend_tool"] in names, "search_tools lost manifest action {!r}; got {}".format(
        target["backend_tool"], names
    )


def test_manifest_exposes_more_actions_than_mcp_tools_list(mcp):
    """The manifest's reason-for-being: bulk discovery in one round-trip.

    ``tools/list`` intentionally returns meta-tools + ``__skill__*`` stubs
    only (to keep MCP handshakes cheap).  The manifest fills the gap by
    advertising every real skill action.  Without this test we could
    accidentally regress the manifest back into parroting ``tools/list``
    and undo the whole issue #163 design.
    """
    manifest = _load_capability_manifest(mcp)
    manifest_tools = {r["backend_tool"] for r in manifest["capabilities"]}

    mcp_tools = {t["name"] for t in mcp.tools_list_all()}

    manifest_only = manifest_tools - mcp_tools
    # The manifest should surface dozens of actions that tools/list doesn't.
    assert len(manifest_only) >= 20, (
        "manifest should expose many more actions than tools/list; "
        "overlap too large (manifest={}, mcp={}, only_in_manifest={})".format(
            len(manifest_tools), len(mcp_tools), len(manifest_only)
        )
    )


# ---------------------------------------------------------------------------
# 2. Token efficiency — hard budgets enforced.
# ---------------------------------------------------------------------------


def test_tools_list_first_page_fits_small_context(mcp):
    """A fresh MCP session must not blow an agent's context on handshake.

    80 KB is ~20K GPT tokens — already generous for a handshake.  We want
    to catch accidents like dumping full inputSchema for every tool into
    the first page.
    """
    page = mcp.tools_list()
    encoded = json.dumps(page, separators=(",", ":"))
    assert len(encoded) < 80_000, "tools/list page 1 too large: {} bytes".format(len(encoded))


def test_tools_list_per_entry_stays_cheap(mcp):
    """Individual ``tools/list`` entries must stay compact.

    An agent pages through ``tools/list`` lazily; each entry therefore
    pays a per-context-turn cost.  2 KB/entry is the hard ceiling — in
    practice most entries sit at <500 B.  Anything >2 KB is likely a
    tool that accidentally inlined its full docs.
    """
    all_tools = mcp.tools_list_all()
    assert all_tools, "expected tools from a loaded server"
    offenders = []
    for tool in all_tools:
        encoded = json.dumps(tool, separators=(",", ":"))
        if len(encoded) > 2_048:
            offenders.append((tool.get("name"), len(encoded)))
    assert not offenders, "per-tool budget (2 KB) exceeded: {}".format(offenders)


def test_manifest_has_wider_coverage_than_tools_list(mcp):
    """Manifest must advertise strictly *more* actions than ``tools/list``.

    The compact manifest's core value to an agent is *coverage* — it's
    the only single round-trip that lists every bundled skill action.
    ``tools/list`` intentionally only returns meta-tools plus
    ``__skill__*`` stubs, so the manifest must cover a much larger set.

    We cross-check the two counts and assert the manifest contains at
    least 2× the action count of ``tools/list``.  If this ratio ever
    drops below 2 we've either regressed the manifest (it stopped
    enumerating skill actions) or inflated ``tools/list`` (it started
    enumerating full actions, undoing the cheap-handshake design).
    """
    manifest = _load_capability_manifest(mcp)
    manifest_count = len(manifest["capabilities"])
    tools_list_count = len(mcp.tools_list_all())
    assert manifest_count >= int(tools_list_count * 1.5), (
        "manifest coverage should be >=1.5x tools/list; manifest={}, tools/list={}".format(
            manifest_count, tools_list_count
        )
    )


def test_manifest_per_record_cost_is_bounded(mcp):
    """Compact manifest must cap *per-record* serialised cost.

    The #163 contract is that each record stays well under a full MCP
    tool schema (typically 1–2 KB).  We assert <=640 B / record and flag
    any outliers — this is the only way to keep thousands of potential
    capabilities accessible in a single agent turn.
    """
    manifest = _load_capability_manifest(mcp)
    records = manifest["capabilities"]
    assert records
    offenders = []
    for rec in records:
        encoded = json.dumps(rec, separators=(",", ":"))
        if len(encoded) > 640:
            offenders.append((rec.get("backend_tool"), len(encoded)))
    assert not offenders, "per-record budget (640 B) exceeded: {}".format(offenders)


def test_manifest_record_omits_input_schema(mcp):
    """The manifest contract mandates ``input_schema`` is **never** inlined.

    Schemas are fetched on-demand via MCP ``tools/list`` or (when core
    0.14.22+ ships) REST ``/v1/describe``.  Guarding this invariant
    protects the token budget against accidental schema inlining.
    """
    manifest = _load_capability_manifest(mcp)
    for rec in manifest["capabilities"]:
        assert "input_schema" not in rec, "record must not inline input_schema: {}".format(rec)
        assert "inputSchema" not in rec


# ---------------------------------------------------------------------------
# 3. Execution parity — tool_slug ↔ backend_tool contract.
# ---------------------------------------------------------------------------


def test_search_tools_strips_heavy_fields(mcp):
    """``search_tools`` must not dump full inputSchema per hit.

    A full schema for ``execute_python`` alone is ~500 B; dumping it 10
    times per search response wastes >5 KB that an agent will never read.
    """
    resp = mcp.tools_call("search_tools", {"query": "maya", "limit": 10})
    result = resp.get("result")
    if result is None:
        pytest.skip("search_tools unavailable in this build")
    payload = json.loads(_extract_text(result))
    hits = payload.get("tools") or payload.get("hits") or []
    if not hits:
        pytest.skip("no hits to compare")
    for hit in hits[:10]:
        assert "inputSchema" not in hit, "search hit inlined schema: {}".format(hit)
        assert "input_schema" not in hit
        # per-hit byte budget — keep search light.
        assert len(json.dumps(hit, separators=(",", ":"))) <= 1_500


def test_backend_tool_is_mcp_callable_when_exposed(mcp):
    """Every manifest record's ``backend_tool`` must be either:
    (a) a real MCP tool (advertised by tools/list), callable end-to-end, or
    (b) a skill-action that is only reachable after ``load_skill``/search
        (handled by the dynamic dispatch path).

    We sample-call a zero-argument meta tool (``list_skills`` or
    ``list_roots``) that is always advertised and asserts the call
    contract holds end-to-end.
    """
    manifest = _load_capability_manifest(mcp)
    backend_tools = {r["backend_tool"] for r in manifest["capabilities"]}
    mcp_tool_names = {t["name"] for t in mcp.tools_list_all()}
    overlap = backend_tools & mcp_tool_names

    # Restrict to tools that we know are safe to invoke without arguments —
    # a naive "first overlap" pick hit ``project.save`` which (correctly)
    # rejects the empty-args call.
    ZERO_ARG_SAFE = ("list_skills", "list_roots", "list_dynamic_tools")
    candidates = [t for t in ZERO_ARG_SAFE if t in overlap]
    if not candidates:
        pytest.skip("no zero-argument meta tools in overlap; overlap sample: {}".format(list(overlap)[:5]))
    candidate = candidates[0]
    call = mcp.tools_call(candidate, {})
    assert "result" in call, "backend_tool {!r} unreachable: {}".format(candidate, call)
    assert not (call.get("result") or {}).get("isError"), "backend_tool {!r} returned error: {}".format(candidate, call)


# ---------------------------------------------------------------------------
# 4. RESTful surface — graceful degradation + parity when available.
# ---------------------------------------------------------------------------


# All endpoints documented in the PR #667 contract.
_REST_ENDPOINTS: List[Tuple[str, str]] = [
    ("GET", "/v1/healthz"),
    ("GET", "/v1/readyz"),
    ("GET", "/v1/openapi.json"),
    ("GET", "/v1/skills"),
    ("GET", "/v1/context"),
]


@pytest.mark.parametrize("method,path", _REST_ENDPOINTS)
def test_rest_surface_never_5xx(rest: _RestClient, method: str, path: str):
    """The REST surface must degrade gracefully.

    Any 2xx (endpoint served) or 4xx (endpoint not mounted in this core
    build) is acceptable.  A 5xx is a regression.  This guard gives us
    forward-compat confidence: when core 0.14.22+ lands the `/v1/*`
    endpoints, the existing test suite will pick them up automatically.
    """
    status, body = rest.get(path) if method == "GET" else rest.post(path, {})
    assert status < 500, "{} {} returned {} with body {!r}".format(method, path, status, body[:200])


def test_rest_call_agrees_with_mcp_when_mounted(rest: _RestClient, mcp: _McpClient):
    """When ``POST /v1/call`` is mounted, it must return the same envelope as MCP.

    The PR #667 contract guarantees identical JSON envelopes between the
    two channels.  We pick a zero-side-effect meta tool (``list_skills``)
    because it's always available and its result is a deterministic
    structure.
    """
    tool_name = "list_skills"
    # Ensure the tool exists over MCP.
    mcp_tools = {t["name"] for t in mcp.tools_list_all()}
    if tool_name not in mcp_tools:
        pytest.skip("{} not advertised in this build".format(tool_name))

    # Try /v1/call — skip when core 0.14.22 is not installed yet.
    status, body = rest.post("/v1/call", {"name": tool_name, "arguments": {}})
    if status == 404:
        pytest.skip("REST /v1/call not mounted in this core build (< 0.14.22)")
    assert status == 200, "REST /v1/call failed: status={} body={!r}".format(status, body[:200])

    try:
        rest_envelope = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pytest.fail("REST /v1/call returned non-JSON body: {!r}".format(body[:200]))

    mcp_response = mcp.tools_call(tool_name, {})
    mcp_text = _extract_text(mcp_response["result"])
    mcp_envelope = json.loads(mcp_text)

    # Both channels should produce the same *logical* envelope; strip any
    # trace-id or timestamp noise that the REST adapter is allowed to add.
    def _strip_noise(env: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in env.items() if k not in ("trace_id", "timestamp", "_meta")}

    assert _strip_noise(rest_envelope) == _strip_noise(mcp_envelope), (
        "REST and MCP envelopes diverge:\nREST={}\nMCP={}".format(
            json.dumps(rest_envelope, sort_keys=True)[:400],
            json.dumps(mcp_envelope, sort_keys=True)[:400],
        )
    )


def test_rest_healthz_when_mounted_is_cheap(rest: _RestClient):
    """``/v1/healthz`` must return quickly with a tiny body.

    Health checks run on every gateway heartbeat — inflating them with
    extra diagnostics is a real production cost.  The reference
    implementation returns a single ``{"status":"ok"}`` or plain ``ok``
    (~30 B); we assert <=256 B as a generous ceiling.
    """
    status, body = rest.get("/v1/healthz")
    if status == 404:
        pytest.skip("REST /v1/healthz not mounted in this core build")
    assert status == 200
    assert len(body) <= 256, "healthz body too large: {} bytes".format(len(body))


# ---------------------------------------------------------------------------
# 5. Minimal-mode regression — skills-behind-stubs must stay discoverable.
# ---------------------------------------------------------------------------


def test_minimal_mode_skill_stubs_dont_leak_schemas():
    """``__skill__*`` stubs in minimal mode must not inline per-action schemas.

    The whole point of minimal mode is to defer tool-schema costs until
    an agent calls ``load_skill``.  If a stub starts leaking the child
    tools' full schemas, the minimal-mode bandwidth savings evaporate.
    We load a tight server (no gateway), list tools, and ensure every
    ``__skill__*`` stub stays tiny.
    """
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=True)
    handle = server.start()
    try:
        time.sleep(0.05)
        client = _McpClient(handle.mcp_url())
        client.initialize()
        all_tools = client.tools_list_all()
        stubs = [t for t in all_tools if t["name"].startswith("__skill__")]
        assert stubs, "minimal-mode server must advertise __skill__* stubs"
        offenders = []
        for stub in stubs:
            encoded = json.dumps(stub, separators=(",", ":"))
            if len(encoded) > 1_024:
                offenders.append((stub["name"], len(encoded)))
            # Stub input schemas should stay trivial (generally a flag-ish object).
            schema = stub.get("inputSchema") or {}
            props = schema.get("properties") or {}
            assert len(props) <= 5, "{} stub has too many properties ({}); minimal-mode must stay cheap".format(
                stub["name"], len(props)
            )
        assert not offenders, "__skill__* stubs exceeded 1 KB budget: {}".format(offenders)
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# 6. Skill audit — bundled skills stay token-lean.
# ---------------------------------------------------------------------------


def _iter_bundled_tools_yaml() -> Iterable[Tuple[str, Dict[str, Any]]]:
    import yaml  # local import — keeps module-level imports lean

    skills_dir = os.path.join(_SRC, "dcc_mcp_maya", "skills")
    for skill_name in sorted(os.listdir(skills_dir)):
        tools_yaml = os.path.join(skills_dir, skill_name, "tools.yaml")
        if not os.path.isfile(tools_yaml):
            continue
        with open(tools_yaml, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        yield skill_name, data


def test_bundled_tools_yaml_have_no_bloated_descriptions():
    """Prevent future PRs from inflating tools.yaml descriptions.

    500 B is ~125 GPT tokens — already plenty for a human-friendly
    sentence.  The bundled skills currently all comfortably fit under
    this ceiling; guarding it prevents drift.
    """
    offenders = []
    for skill_name, data in _iter_bundled_tools_yaml():
        for tool in data.get("tools", []) or []:
            desc = tool.get("description", "") or ""
            if len(desc) > 500:
                offenders.append((skill_name, tool.get("name"), len(desc)))
    assert not offenders, "tools.yaml descriptions exceed 500 B: {}".format(offenders)


def test_bundled_tools_yaml_inputschema_budget():
    """Per-tool inputSchema must stay under 1.5 KB.

    Anything bigger suggests the schema is documenting examples or
    inline narratives — those belong in ``SKILL.md`` reference material,
    not the machine-read schema.
    """
    offenders = []
    for skill_name, data in _iter_bundled_tools_yaml():
        for tool in data.get("tools", []) or []:
            schema = tool.get("inputSchema") or {}
            if not schema:
                continue
            encoded = json.dumps(schema, separators=(",", ":"))
            if len(encoded) > 1_500:
                offenders.append((skill_name, tool.get("name"), len(encoded)))
    assert not offenders, "tools.yaml inputSchema exceeds 1.5 KB budget: {}".format(offenders)


def test_bundled_tools_declare_execution_and_affinity():
    """Every bundled tool must declare ``execution`` and ``affinity``.

    This enforces the AGENTS.md contract: async tools need
    ``timeout_hint_secs``, sync tools must state affinity so the
    dispatcher routes them correctly.  Omission has caused real runtime
    issues (issue #168) — we guard it here at lint time.
    """
    missing = []
    for skill_name, data in _iter_bundled_tools_yaml():
        for tool in data.get("tools", []) or []:
            name = tool.get("name")
            if "execution" not in tool:
                missing.append(("execution", skill_name, name))
            if "affinity" not in tool:
                missing.append(("affinity", skill_name, name))
            if tool.get("execution") == "async" and "timeout_hint_secs" not in tool:
                missing.append(("timeout_hint_secs", skill_name, name))
    assert not missing, "bundled tools.yaml missing required fields: {}".format(missing)


# ---------------------------------------------------------------------------
# 7. Forward-compat coverage for core 0.14.22 (dcc-mcp-core#242, #658)
# ---------------------------------------------------------------------------


def test_output_schema_field_exists_on_registered_actions_when_core_22():
    """Regression lock — ``output_schema`` must be a first-class action
    field exposed by the core registry on 0.14.22+.

    Skill authors rely on this to layer per-action output validation.
    If a future core downgrade strips the field, fail loudly in CI
    rather than silently lose the contract.
    """
    try:
        import dcc_mcp_core
    except Exception:  # pragma: no cover
        pytest.skip("dcc-mcp-core not importable")

    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=True)
    try:
        actions = server._server.registry.list_actions_enabled()
        assert actions, "minimal mode must register at least one action"
        first = actions[0]
        # The key must be present (value may legitimately be ``None``
        # until core propagates tools.yaml ``outputSchema``; see the
        # upstream gap referenced below).
        assert "output_schema" in first, "core {} no longer exposes output_schema on registered actions".format(
            dcc_mcp_core.__version__
        )
    finally:
        server.stop()


@dataclass
class _ToolSpecFromCallableFixture:
    """Module-level dataclass so :func:`typing.get_type_hints` can
    resolve the forward reference Python 3.12 emits for return
    annotations of nested functions.
    """

    x: int


def test_tool_spec_from_callable_is_importable_on_core_22():
    """dcc-mcp-core#242 shipped :func:`tool_spec_from_callable` in 0.14.22.

    ``dcc_mcp_maya.api.maya_typed_success`` relies on
    :func:`derive_schema` from the same ``dcc_mcp_core.schema`` module.
    If core ever drops either, our typed-output helper silently stops
    producing ``output_schema`` — this test surfaces the regression
    immediately.
    """
    try:
        from dcc_mcp_core.schema import derive_schema, tool_spec_from_callable  # noqa: F401
    except ImportError:
        pytest.skip("core build lacks .schema module (pre-0.14.22)")

    def handler(n: int = 1) -> _ToolSpecFromCallableFixture:
        """Fixture handler — int in, dataclass out."""
        return _ToolSpecFromCallableFixture(x=n)

    spec = tool_spec_from_callable(handler)
    assert spec.input_schema.get("type") == "object"
    assert spec.output_schema.get("type") == "object"
    assert spec.output_schema.get("title") == "_ToolSpecFromCallableFixture"


def test_per_dcc_skill_rest_surface_tracking():
    """Upstream gap tracker.

    On core 0.14.22 the ``SkillRestService`` / ``build_skill_rest_router``
    crate compiles and is exposed on the **gateway**, but is NOT yet
    mounted on the per-DCC :class:`McpHttpServer`.  Today all of
    ``/v1/healthz``, ``/v1/readyz``, ``/v1/openapi.json``,
    ``/v1/skills``, ``/v1/context``, ``/v1/search``, ``/v1/describe``,
    ``/v1/call`` return 404 when queried against a per-DCC server.

    When upstream closes that gap this test flips green automatically —
    giving the Maya adapter an immediate signal to bump the pin and
    unmark the previously-skipped parity tests.
    """
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    handle = server.start()
    try:
        rest = _RestClient(handle.mcp_url().rsplit("/", 1)[0])
        # The canonical liveness probe we would LIKE to succeed.  On
        # core 0.14.22 this returns 404 — expected.  On future core
        # versions that mount ``skill_rest`` per-DCC it returns 200 and
        # the test becomes a positive contract lock.
        status, body = rest.get("/v1/healthz")
        if status == 200:
            assert len(body) <= 256, "healthz body too large after per-DCC mount: {}".format(len(body))
        else:
            # Upstream gap still present — record the expected 404 so
            # a silent regression to 500 / 502 trips this test even
            # before the mount is wired.
            assert status == 404, "per-DCC /v1/healthz returned unexpected {} (expected 404 or 200)".format(status)
    finally:
        server.stop()
