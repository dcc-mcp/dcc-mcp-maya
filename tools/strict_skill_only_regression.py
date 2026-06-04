from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    idx = (len(sorted_values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return float(sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac)


def _summary_ms(values_ms: Sequence[float]) -> Dict[str, float]:
    if not values_ms:
        return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    ordered = sorted(values_ms)
    return {
        "avg": float(statistics.fmean(values_ms)),
        "p50": _percentile(ordered, 0.50),
        "p95": _percentile(ordered, 0.95),
        "p99": _percentile(ordered, 0.99),
        "max": float(ordered[-1]),
    }


@dataclass
class GatewayClient:
    base_url: str
    timeout_secs: int = 120

    def _post(self, route: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + route
        raw = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=raw,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_secs) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {url}: {payload[:500]}") from exc

    def search(self, query: str, *, loaded_only: bool = False, limit: int = 25) -> Dict[str, Any]:
        return self._post("/v1/search", {"query": query, "loaded_only": loaded_only, "limit": limit})

    def describe(self, tool_slug: str) -> Dict[str, Any]:
        return self._post("/v1/describe", {"tool_slug": tool_slug, "include_schema": True})

    def call(self, tool_slug: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._post("/v1/call", {"tool_slug": tool_slug, "arguments": arguments or {}})


def _extract_slug(hit: Dict[str, Any]) -> str:
    return str(hit.get("tool_slug") or hit.get("slug") or hit.get("name") or "")


def _extract_action(hit: Dict[str, Any]) -> str:
    return str(
        hit.get("backend_tool")
        or hit.get("action")
        or hit.get("tool_slug")   # slug often encodes the action (e.g. "maya_scene__new_scene")
        or hit.get("slug")
        or hit.get("name")
        or ""
    )


def _pick_slug_for_action(search_result: Dict[str, Any], action_name: str) -> str:
    hits = list(search_result.get("hits") or [])

    # 1. Exact backend_tool/action match (preferred)
    for hit in hits:
        action = _extract_action(hit)
        if action == action_name:
            slug = _extract_slug(hit)
            if slug:
                return slug

    # 2. Substring match: slug contains the action name
    for hit in hits:
        slug = _extract_slug(hit)
        if slug and action_name in slug:
            return slug

    # 3. Last-resort: any hit whose action/slug/name mentions the last segment
    #    of the action name (e.g. "get_scene_info" from "maya_scene__get_scene_info")
    short_name = action_name.rsplit("__", 1)[-1] if "__" in action_name else action_name
    for hit in hits:
        action = _extract_action(hit)
        slug = _extract_slug(hit)
        if short_name and (short_name in action or short_name in slug):
            return slug

    raise RuntimeError(f"Cannot resolve slug for action={action_name!r}; hits={hits[:3]!r}")


def _ensure_call_success(resp: Dict[str, Any], op: str) -> Dict[str, Any]:
    output = resp.get("output")
    if isinstance(output, dict) and output.get("success") is True:
        return output
    raise RuntimeError(f"{op} failed: {json.dumps(resp, ensure_ascii=False)[:1000]}")


def _resolve_base_url(cli_base_url: Optional[str]) -> str:
    if cli_base_url:
        return cli_base_url.rstrip("/")
    env_base = os.environ.get("DCC_MCP_GATEWAY_BASE_URL", "").strip()
    if env_base:
        return env_base.rstrip("/")
    return "http://127.0.0.1:9765"


@dataclass
class SlugCache:
    """Caches resolved tool slugs to avoid redundant search+describe round-trips.

    Each unique action name is resolved once via search+describe; subsequent
    lookups return the cached slug.  This matters for workloads with hundreds
    of typed calls against the same set of actions.
    """

    _cache: Dict[str, str] = field(default_factory=dict)

    def resolve(self, client: GatewayClient, action_name: str) -> str:
        if action_name not in self._cache:
            search = client.search(action_name, loaded_only=False, limit=20)
            slug = _pick_slug_for_action(search, action_name)
            client.describe(slug)
            self._cache[action_name] = slug
        return self._cache[action_name]

    def preload_actions(self, client: GatewayClient, *action_names: str) -> None:
        """Eagerly resolve multiple actions so later calls hit the cache."""
        for name in action_names:
            self.resolve(client, name)


def _load_skill(client: GatewayClient, slug_cache: SlugCache, skill_name: str) -> None:
    slug = slug_cache.resolve(client, "load_skill")
    resp = client.call(slug, {"skill_name": skill_name})
    _ensure_call_success(resp, f"load_skill({skill_name})")


def _verify_arbitrary_script_blocked(client: GatewayClient, slug_cache: SlugCache) -> Dict[str, Any]:
    checks: Dict[str, Any] = {"execute_python": None, "execute_mel": None}
    for action_name, args in (
        ("maya_scripting__execute_python", {"code": "print('blocked-check')", "capture_output": True}),
        ("maya_scripting__execute_mel", {"code": "print \"blocked-check\";"}),
    ):
        slug = slug_cache.resolve(client, action_name)
        resp = client.call(slug, args)
        output = resp.get("output") if isinstance(resp, dict) else None
        blocked = isinstance(output, dict) and output.get("success") is False
        checks["execute_python" if "python" in action_name else "execute_mel"] = {
            "slug": slug,
            "blocked": bool(blocked),
            "response": output,
        }
        if not blocked:
            raise RuntimeError(
                "Strict skill-only policy check failed: arbitrary script tool was not blocked. "
                "Set DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON=1 and DCC_MCP_MAYA_DISABLE_EXECUTE_MEL=1 "
                "(or DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1)."
            )
    return checks


def _typed_call(
    client: GatewayClient,
    slug_cache: SlugCache,
    action_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    slug = slug_cache.resolve(client, action_name)
    resp = client.call(slug, arguments)
    return _ensure_call_success(resp, action_name)


def _run_workload(client: GatewayClient, slug_cache: SlugCache, out_dir: Path) -> Dict[str, Any]:
    # --- Phase 1: Load skills ---
    skills = ("maya-scene", "maya-primitives", "maya-materials", "maya-animation", "maya-geometry")
    for skill in skills:
        _load_skill(client, slug_cache, skill)
        print(f"[workload] loaded skill: {skill}")

    # --- Pre-resolve all action slugs so the tight loops never search+describe ---
    _all_actions = (
        "maya_scene__new_scene",
        "maya_primitives__create_sphere",
        "maya_primitives__set_transform",
        "maya_materials__create_material",
        "maya_materials__assign_material",
        "maya_animation__set_keyframe",
        "maya_scene__set_selection",
        "maya_geometry__export_fbx",
    )
    slug_cache.preload_actions(client, *_all_actions)
    print("[workload] pre-resolved all action slugs (cached)")

    # --- Phase 2: Create 150 objects ---
    _typed_call(client, slug_cache, "maya_scene__new_scene", {"force": True})

    created: List[str] = []
    for i in range(150):
        name = f"perf_ball_{i + 1:03d}"
        _typed_call(client, slug_cache, "maya_primitives__create_sphere", {"radius": 0.25, "name": name})
        _typed_call(
            client,
            slug_cache,
            "maya_primitives__set_transform",
            {"object_name": name, "translate": [float(i % 15) * 2.0, float(i // 15) * 1.2, 0.0]},
        )
        created.append(name)
        if (i + 1) % 50 == 0:
            print(f"[workload] created {i + 1}/150 objects")

    # --- Phase 3: Create and assign materials ---
    mats = []
    for idx in range(3):
        material_name = f"perf_mat_{idx + 1:02d}"
        _typed_call(client, slug_cache, "maya_materials__create_material", {"material_type": "lambert", "name": material_name})
        mats.append(material_name)
    print(f"[workload] created {len(mats)} materials, assigning to {len(created)} objects...")

    for idx, node in enumerate(created):
        _typed_call(
            client,
            slug_cache,
            "maya_materials__assign_material",
            {"material_name": mats[idx % len(mats)], "objects": [node]},
        )

    # --- Phase 4: Set keyframes ---
    for i in range(180):
        node = created[i % len(created)]
        frame = 1 + i
        value = float((i % 20) - 10)
        _typed_call(
            client,
            slug_cache,
            "maya_animation__set_keyframe",
            {"object_name": node, "attribute": "translateY", "time": frame, "value": value},
        )
        if (i + 1) % 60 == 0:
            print(f"[workload] set {i + 1}/180 keyframes")

    # --- Phase 5: Select all and export FBX ---
    _typed_call(client, slug_cache, "maya_scene__set_selection", {"objects": created})
    fbx_path = (out_dir / "strict_skill_only_perf.fbx").resolve()
    export_res = _typed_call(
        client,
        slug_cache,
        "maya_geometry__export_fbx",
        {
            "path": str(fbx_path).replace("\\", "/"),
            "selected_only": True,
            "bake_animation": True,
            "start_frame": 1,
            "end_frame": 180,
            "fbx_version": "FBX202000",
            "up_axis": "y",
        },
    )
    print(f"[workload] FBX exported: {fbx_path}")

    return {
        "objects_created": len(created),
        "materials_created": len(mats),
        "keyframes_set": 180,
        "fbx": {
            "path": str(fbx_path),
            "size_bytes": export_res.get("context", {}).get("size_bytes", 0),
            "applied_options": export_res.get("context", {}).get("applied_options", {}),
        },
    }


def _run_read_soak(client: GatewayClient, slug_cache: SlugCache, iterations: int) -> Dict[str, Any]:
    read_actions = [
        ("maya_scene__get_scene_info", {}),
        ("maya_scene__list_objects", {"object_type": "transform"}),
        ("maya_materials__list_materials", {}),
        ("maya_animation__query_scene_time_info", {}),
        ("maya_scene__get_selection", {}),
    ]

    slug_cache.preload_actions(client, *(a for a, _ in read_actions))

    latencies: List[float] = []
    failures: List[Dict[str, Any]] = []

    for idx in range(iterations):
        action, args = read_actions[idx % len(read_actions)]
        t0 = time.perf_counter()
        try:
            _typed_call(client, slug_cache, action, dict(args))
        except Exception as exc:  # noqa: BLE001
            failures.append({"iteration": idx + 1, "action": action, "error": str(exc)})
        finally:
            latencies.append((time.perf_counter() - t0) * 1000.0)

        if (idx + 1) % 100 == 0:
            print(f"[soak] {idx + 1}/{iterations} iterations")

    summary = _summary_ms(latencies)
    return {
        "iterations": iterations,
        "avg_ms": summary["avg"],
        "p50_ms": summary["p50"],
        "p95_ms": summary["p95"],
        "p99_ms": summary["p99"],
        "max_ms": summary["max"],
        "failure_count": len(failures),
        "failures": failures,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    base_url = _resolve_base_url(args.base_url)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = GatewayClient(base_url=base_url, timeout_secs=args.timeout_secs)
    slug_cache = SlugCache()

    started = time.perf_counter()
    report: Dict[str, Any] = {
        "issue": "PIP-481",
        "suite": "maya_strict_skill_only_regression",
        "started_at": _utc_now(),
        "gateway_base_url": base_url,
        "policy": "search -> load_skill/activate group -> describe -> call typed tools (no execute_python/execute_mel)",
        "config": {
            "soak_iterations": args.soak_iterations,
            "object_count_target": 150,
            "keyframe_count_target": 180,
        },
    }

    print("=" * 60)
    print("[suite] Maya Strict Skill-Only Regression Suite — PIP-481")
    print(f"[suite] Gateway: {base_url}")
    print("=" * 60)

    print("\n--- Policy Guard ---")
    report["policy_guard"] = _verify_arbitrary_script_blocked(client, slug_cache)
    print("[policy_guard] Both execute_python and execute_mel are blocked ✓")

    print("\n--- Typed Workload ---")
    report["workload"] = _run_workload(client, slug_cache, out_dir)

    print("\n--- Read-Only Soak ---")
    report["soak"] = _run_read_soak(client, slug_cache, args.soak_iterations)

    report["finished_at"] = _utc_now()
    report["duration_secs"] = round(time.perf_counter() - started, 3)
    report["success"] = report["soak"]["failure_count"] == 0

    print(f"\n[suite] Duration: {report['duration_secs']}s")
    print(f"[suite] Success: {report['success']}")
    return report


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict skill-only Maya performance regression runner")
    parser.add_argument("--base-url", default=None, help="Gateway REST base URL (default: env DCC_MCP_GATEWAY_BASE_URL or http://127.0.0.1:9765)")
    parser.add_argument("--output-dir", default="artifacts/perf", help="Directory for FBX + JSON report")
    parser.add_argument("--report", default="", help="Optional explicit report path")
    parser.add_argument("--soak-iterations", type=int, default=500, help="Read-only soak iteration count")
    parser.add_argument("--timeout-secs", type=int, default=120, help="HTTP timeout per request")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        report = run(args)
    except Exception as exc:  # noqa: BLE001
        failure = {
            "suite": "maya_strict_skill_only_regression",
            "started_at": _utc_now(),
            "success": False,
            "error": str(exc),
        }
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report) if args.report else out_dir / ("strict_skill_only_regression_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"REPORT_PATH={report_path}")
    return 0 if report.get("success") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
