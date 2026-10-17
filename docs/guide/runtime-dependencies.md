# Maya runtime dependencies

Maya provides Python. The adapter's required runtime closure is the standard
library, Maya/plugin-owned modules, and first-party DCC-MCP Core/server. Build
and development dependencies are separate. The enforceable repository policy is
in [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md#adapter-runtime-dependency-boundary).

## Version checks without a runtime package

`_version_contract.py` is an import-light, Python 3.7-compatible leaf. It implements
exact package-version identity and ordering, plus this repository's one fixed
stable `>= minimum, < maximum` range. It is **not** a general requirement,
marker, resolver, or specifier library. Build tooling still uses `packaging`.
The implementation is independently written against the
[Python version specification](https://packaging.python.org/en/latest/specifications/version-specifiers/).

Existing ASCII public exact-version inputs retain their meaning: arbitrary-length
numeric releases and trailing-zero equality; leading-zero and `v` normalization;
epochs; alpha/beta/rc aliases; pre/dev/post combinations; implicit post releases
such as `0.20.0-1`; and case/separator/numeric normalization of local labels.
A full-string parse rejects malformed input rather than extracting a numeric
prefix. Epochs and local labels remain part of provenance identity. Non-ASCII
local-label lookalikes such as `1.0+K` fail closed: packaging 24.0 accidentally
accepted these out-of-spec identifiers through Unicode case matching, whereas
26.3 rejects them. This explicit hardening is the exact-parser compatibility
difference; the standardized ASCII spellings remain supported.

| Consumer | Operation / compatibility policy |
| --- | --- |
| `headless.serve_headless` | Exact ordering against the historic `0.19.64` floor. Its rc/dev versions remain below that floor; post/local versions remain above it. A later prerelease still orders above the historic floor. |
| Install lifecycle and setup verification | Canonical `>=0.20.0,<0.21.0` stable range. Final/post/local forms inside the bounds are accepted; all pre/dev forms are rejected. |
| Embedded Core provenance | Exact identity equality, including epoch/local labels, with existing duplicate-header, immutable snapshot, path and hash checks unchanged. |
| Startup diagnostics | Normalization and numeric ordering; invalid values remain nonfatal and deterministically ordered. |
| Module assembler | Build-only `packaging` validates wheel metadata and orders PyPI candidates. Invalid/pre/dev candidates are skipped individually instead of making the entire lookup fall back to its floor. |

The explicit stable-only lifecycle policy matches `packaging 24.0`, bundled in
0.9.36. An unbounded pip-installed `packaging>=21.3` previously made this depend
on the host environment: 26.3 automatically admitted an interior prerelease such
as `0.20.1rc1`. Such pip environments now consistently reject that input. This is
an intentional compatibility stabilization, not a claim that all historical
`packaging` releases behaved identically. The headless ordering policy is unchanged.

Core's current public `SemVer` intentionally ignores prerelease suffixes; its
private helper also truncates release components. Neither can safely replace
exact metadata identity. The leaf can move to a public import-light Core API
later; adapters must not grow independent general-purpose resolvers.

## Gates and distribution size

- `test_version_contract.py` compares exact-version normalization, ordering,
  identity and explicit stable-range behavior with the dev-only `packaging`
  oracle, including aliases and malformed input.
- `test_adapter_runtime_dependencies.py` audits required/runtime-extra
  declarations and adapter/bootstrap imports. Host-owned integrations and the
  existing narrowly scoped optional debugger/YAML/metadata fallbacks are
  distinguished from mandatory third-party dependencies.
- Release and Mayapy CI run `test_offline_module_bootstrap.py` against both actual
  portable/pipeline ZIPs. Both runtime roots are inspected. A fresh `-I -S`
  process exercises bootstrap, the public headless entry point and full Core
  provenance validation without `pip`, site-packages or `packaging`. The smoke
  models the licensed host/server; it does not replace licensed-host E2E tests.

A controlled Linux build using the same adapter version (0.9.36), Core 0.20.44
and server 0.20.45 measured:

| Archive | Before | After | Saved |
| --- | ---: | ---: | ---: |
| Portable | 105,998,457 bytes | 105,893,395 bytes | 105,062 bytes (0.099%) |
| Pipeline | 105,996,724 bytes | 105,891,662 bytes | 105,062 bytes (0.099%) |

Removing `packaging` from both runtime roots removes 46 vendor files and 348,344
uncompressed bytes. The new small version leaf offsets part of that saving.
Native Core and server payloads still dominate archive size. Their platform/ABI
layout and shared Runtime distribution need separate review; this change does
not delete Python 3.7 compatibility payloads or replace first-party runtimes.
