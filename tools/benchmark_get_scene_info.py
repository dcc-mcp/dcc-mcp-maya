from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
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


def _summary(values_ms: Sequence[float]) -> Dict[str, float]:
    if not values_ms:
        return {"avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "max_ms": 0.0}
    ordered = sorted(values_ms)
    return {
        "avg_ms": float(statistics.fmean(values_ms)),
        "p50_ms": _percentile(ordered, 0.50),
        "p95_ms": _percentile(ordered, 0.95),
        "p99_ms": _percentile(ordered, 0.99),
        "max_ms": float(ordered[-1]),
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


def _slug(hit: Dict[str, Any]) -> str:
    return str(hit.get("tool_slug") or hit.get("slug") or hit.get("name") or "")


def _action(hit: Dict[str, Any]) -> str:
    return str(hit.get("backend_tool") or hit.get("action") or hit.get("name") or "")


def _resolve_action(client: GatewayClient, action_name: str) -> str:
    result = client.search(action_name, loaded_only=False, limit=20)
    for hit in result.get("hits") or []:
        if _action(hit) == action_name:
            slug = _slug(hit)
            if slug:
                client.describe(slug)
                return slug
    for hit in result.get("hits") or []:
        slug = _slug(hit)
        if action_name in slug:
            client.describe(slug)
            return slug
    raise RuntimeError(f"Could not resolve action {action_name!r}: {result!r}")


def _ensure_success(resp: Dict[str, Any], op: str) -> Dict[str, Any]:
    output = resp.get("output")
    if isinstance(output, dict) and output.get("success") is True:
        return output
    raise RuntimeError(f"{op} failed: {json.dumps(resp, ensure_ascii=False)[:1000]}")


def _load_skill(client: GatewayClient, skill_name: str) -> None:
    load_skill = _resolve_action(client, "load_skill")
    _ensure_success(client.call(load_skill, {"skill_name": skill_name}), f"load_skill({skill_name})")


def _prepare_scene(client: GatewayClient, object_count: int) -> None:
    _load_skill(client, "maya-scene")
    _load_skill(client, "maya-primitives")
    new_scene = _resolve_action(client, "maya_scene__new_scene")
    create_sphere = _resolve_action(client, "maya_primitives__create_sphere")
    set_transform = _resolve_action(client, "maya_primitives__set_transform")
    _ensure_success(client.call(new_scene, {"force": True}), "new_scene")
    for idx in range(object_count):
        name = f"scene_info_bench_{idx + 1:03d}"
        _ensure_success(client.call(create_sphere, {"radius": 0.25, "name": name}), "create_sphere")
        _ensure_success(
            client.call(
                set_transform,
                {"object_name": name, "translate": [float(idx % 15) * 2.0, float(idx // 15), 0.0]},
            ),
            "set_transform",
        )


def _measure_mode(client: GatewayClient, tool_slug: str, mode: str, iterations: int) -> Dict[str, Any]:
    latencies: List[float] = []
    payload_sizes: List[int] = []
    failures: List[str] = []
    args = {"detail_mode": mode}
    for _ in range(iterations):
        started = time.perf_counter()
        try:
            resp = client.call(tool_slug, args)
            payload_sizes.append(len(json.dumps(resp, ensure_ascii=False).encode("utf-8")))
            _ensure_success(resp, f"get_scene_info({mode})")
        except Exception as exc:  # noqa: BLE001
            failures.append(str(exc))
        finally:
            latencies.append((time.perf_counter() - started) * 1000.0)
    summary = _summary(latencies)
    summary.update(
        {
            "iterations": iterations,
            "payload_bytes_avg": int(statistics.fmean(payload_sizes)) if payload_sizes else 0,
            "payload_bytes_max": max(payload_sizes) if payload_sizes else 0,
            "failure_count": len(failures),
            "failures": failures[:10],
        }
    )
    return summary


def _base_url(cli_value: Optional[str]) -> str:
    if cli_value:
        return cli_value.rstrip("/")
    return os.environ.get("DCC_MCP_GATEWAY_BASE_URL", "http://127.0.0.1:9765").rstrip("/")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    client = GatewayClient(_base_url(args.base_url), timeout_secs=args.timeout_secs)
    if args.prepare_scene:
        _prepare_scene(client, args.object_count)
    _load_skill(client, "maya-scene")
    get_scene_info = _resolve_action(client, "maya_scene__get_scene_info")
    modes = ["lightweight", "standard", "full"]
    return {
        "issue": "PIP-479",
        "suite": "benchmark_get_scene_info",
        "started_at": _utc_now(),
        "gateway_base_url": client.base_url,
        "config": {
            "iterations": args.iterations,
            "object_count": args.object_count if args.prepare_scene else "existing_scene",
            "prepared_scene": bool(args.prepare_scene),
        },
        "modes": {mode: _measure_mode(client, get_scene_info, mode, args.iterations) for mode in modes},
        "finished_at": _utc_now(),
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark maya_scene__get_scene_info detail modes through gateway REST")
    parser.add_argument("--base-url", default=None, help="Gateway REST base URL")
    parser.add_argument("--iterations", type=int, default=100, help="Calls per detail mode")
    parser.add_argument("--object-count", type=int, default=150, help="Object count when --prepare-scene is set")
    parser.add_argument("--prepare-scene", action="store_true", help="Create a deterministic benchmark scene first")
    parser.add_argument("--output-dir", default="artifacts/perf", help="Directory for JSON report")
    parser.add_argument("--report", default="", help="Optional explicit report path")
    parser.add_argument("--timeout-secs", type=int, default=120, help="HTTP timeout per request")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    report = run(args)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report) if args.report else out_dir / ("get_scene_info_benchmark_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"REPORT_PATH={report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
