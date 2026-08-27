# dcc-mcp-maya Install SOP v1

This is the owning-repository install contract for Autodesk Maya. The stable
catalog route is
`https://raw.githubusercontent.com/dcc-mcp/dcc-mcp-maya/main/install.md`.

## Requirements

- Autodesk Maya and its exact `mayapy` interpreter.
- `dcc-mcp-maya` installed in that interpreter, with
  `dcc-mcp-core>=0.19.45,<1.0.0`.
- Write access to the selected Maya user profile.
- Close Maya before replacing or removing a loaded module on Windows.

Install the Python package with the target interpreter first:

```bash
mayapy -m pip install --upgrade dcc-mcp-maya
```

The legacy repository setup helper remains available for source checkouts, but
the standard lifecycle below is the agent-facing contract.

## Supported versions

Maya 2020 through 2027 locations are discovered and classified through a real
`mayapy` probe. The selected build must provide Python 3.7 or newer; a legacy
Python 2 Maya 2020/2021 build fails preflight instead of receiving incompatible
files. Maya 2022's Python 3.7 remains supported. The installer checks the host,
interpreter, adapter import, and minimum Core version before writing any file.

The host and profile boundaries are explicit on all three platforms:

- Windows: `C:\Program Files\Autodesk\Maya2025` and
  `%USERPROFILE%\Documents\maya`.
- macOS: `/Applications/Autodesk/maya2025/Maya.app` and
  `~/Library/Preferences/Autodesk/maya`.
- Linux: `/usr/autodesk/maya2025` and `~/maya`.

## Agent quick path

Always resolve and inspect a non-mutating plan first:

```bash
dcc-mcp-maya install --json --dry-run --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy"
```

Both paths are overrides. If omitted, discovery checks the Maya environment,
`mayapy` on `PATH`, and the standard Maya 2020-2027 installation locations;
the resolved paths and selection source remain explicit in the JSON plan.

Review `host`, `python`, `install_state`, `steps`, and the executable
`next_steps`. Execute the same validated target only with explicit consent:

```bash
dcc-mcp-maya install --json --yes --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy"
```

Exit codes are stable: `0` success, `10` preflight, `20` acquisition, `30`
install/rollback failure, `40` verification failure, and `50`
requires-restart. Planning never writes. Re-running install converges; a
partial install is classified as a repair.

## Manual path

The lifecycle command stages a complete Maya module tree before commit. It
installs the adapter package, `dcc_mcp_maya_plugin.py`, the packaged
`userSetup.py`, and an absolute `dcc_mcp_maya.mod` descriptor. It also writes a
bounded managed block to the profile `scripts/userSetup.py`.

To consume an immutable released module ZIP instead of assembling the module
from the installed wheel, add `--module-zip /absolute/path/to/archive.zip` to
both the plan and execution commands. ZIP paths, symlinks, encryption, expanded
bytes, and file count are bounded and validated before the profile is created;
the receipt records the archive path and SHA-256.

The receipt records the module tree, descriptor, managed userSetup state,
selected interpreter, Maya version, adapter/Core versions, hashes, and the
prior userSetup content. Replacement is stage -> previous-state backup ->
commit; any failed commit triggers rollback to the complete previous state.
There is no delete-then-copy window.

For a repository checkout, the old helper is compatibility-only:

```bash
python skills/dcc-mcp-maya-setup/scripts/setup_dcc_mcp_maya.py --mayapy "/absolute/path/to/mayapy"
```

## Status

```bash
dcc-mcp-maya status --json --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy"
```

`fresh`, `current`, `upgrade`, and `partial` are reported from the receipt and
artifact hashes. Unknown unreceipted files are never removed automatically.

## Verify

```bash
dcc-mcp-maya verify --json --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy" --timeout 30
```

Verification fails closed through these boundaries:

1. Receipt ownership and artifact hashes.
2. Adapter, Core, and Maya imports in the exact target interpreter.
3. Captured startup errors from `capture_bootstrap_errors`.
4. Core `wait_for_sidecar_ready` followed by the typed `host.ping` probe.

Only all four gates produce `directly_usable: true`. A healthy process or an
HTTP listener alone is not Maya readiness. If Maya is not running, exit `40`
is expected and `next_steps` provides the exact launch and verify commands.

The fixed GUI diagnostic from the dependent bootstrap work remains available:

```bash
mayapy -m dcc_mcp_maya.gui_bootstrap launch --maya-executable "/absolute/path/to/maya" --timeout 120
```

It captures ordered plug-in/registry/sidecar stages without changing Plug-in
Manager Auto Load or using UI automation.

## Upgrade

Upgrade requires an existing valid receipt:

```bash
dcc-mcp-maya upgrade --json --dry-run --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy"
dcc-mcp-maya upgrade --json --yes --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy"
```

The upgrade uses the same staged transaction and rollback path as install. It
preserves the original pre-install userSetup state across repeated upgrades.

## Uninstall

Plan, then consume only the matching receipt:

```bash
dcc-mcp-maya uninstall --json --dry-run --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy"
dcc-mcp-maya uninstall --json --yes --dcc-path "/absolute/path/to/Maya" --python "/absolute/path/to/mayapy"
```

Uninstall removes only receipted module content and restores the prior
userSetup state. A missing receipt or modified owned artifact fails closed.
Repeated uninstall is idempotent. A Windows file lock returns exit `50` and
requires Maya to close/restart before retrying.

## Troubleshooting

- `mayapy_missing`: pass the exact bundled interpreter with `--python`.
- `unsupported_maya_version`: select Maya 2020-2027; do not override the
  detected result with a guessed version.
- `core_version_unsupported` or `target_import_failed`: install the adapter and
  Core into the selected `mayapy`, then repeat the dry run.
- `bootstrap_error_captured`: inspect the reported host-errors log and the
  staged GUI bootstrap log before retrying.
- `sidecar_unavailable`: start Maya, wait for the deferred userSetup/plugin
  load, then run verify again.
- `windows_file_lock`: close every Maya process that loaded this module, then
  retry the same receipted operation.
- `receipt_target_mismatch` or modified artifacts: select the original host and
  profile; do not delete unknown files to force success.
