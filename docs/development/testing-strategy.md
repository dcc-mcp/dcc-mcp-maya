# Testing Strategy

The test suite should prove two contracts:

1. The happy path performs the Maya operation the user asked for.
2. The failure path returns a predictable, actionable error envelope instead of
   crashing Maya, hanging a request, or silently succeeding.

## Keep

- E2E tests that cross a real boundary: mayapy skill execution, MCP HTTP,
  plugin load/unload, sidecar lifecycle, gateway discovery, readiness, and
  cancellation.
- Unit tests for pure decision logic that is hard to trigger reliably in Maya:
  env resolution, schema/manifest shaping, port selection, registry cleanup,
  prompt guards, and result-envelope normalisation.
- Lint-style tests that enforce repository-wide invariants: skill metadata,
  Python 3.7 syntax, docs parity, and forbidden imports.

## Reduce Or Replace

- Bare importability checks should usually become behaviour checks. Import tests
  are only worth keeping for public API compatibility or optional core symbols.
- Tests that assert only `is not None`, `hasattr`, or `"success" in result`
  should assert the full contract: `success`, `message`, `error`, important
  `context` keys, and the side effect that did or did not happen.
- Mock-heavy tests that duplicate the implementation line by line should move
  up one layer when possible, especially for skills. Prefer calling the script
  entry point with a small fake `maya.cmds` surface.

## Error Envelope Checklist

Every skill that validates input or touches Maya state should have at least one
negative-path test that checks:

- `success is False`
- a stable `message`
- useful `error` text
- `context.possible_solutions` when the caller can fix the request
- no mutation happened after validation failed

E2E tests should cover representative failures too, not only successful Maya
operations. Good examples are missing nodes, invalid transform vectors, syntax
errors, disabled arbitrary execution, dirty-scene `cmds.file` prompts, and HTTP
tool calls that return structured failure payloads.

## Current Gaps

- More mayapy E2E should exercise failure paths for scene, geometry, material,
  render, and pipeline skills.
- HTTP E2E should include representative structured failures for both MCP
  `tools/call` and gateway REST once the gateway endpoint is available in CI.
- Some older tests still only prove a symbol exists. Convert them opportunistically
  when touching the surrounding feature.
