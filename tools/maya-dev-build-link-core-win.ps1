# Build dcc-mcp-core with the target Maya's mayapy, then link core + dcc-mcp-maya into
# %USERPROFILE%\Documents\maya\modules\dcc-mcp-maya for live debugging (no wheel copy).
#
# Prerequisites: Rust (cargo) on PATH, Git, optional vx on PATH for stubgen fallback.
#
# Usage:
#   .\tools\maya-dev-build-link-core-win.ps1 -MayaVersion 2025
#   .\tools\maya-dev-build-link-core-win.ps1 -MayaVersion 2025 -CoreRepo G:\path\to\dcc-mcp-core
#   .\tools\maya-dev-build-link-core-win.ps1 -MayaVersion 2025 -LaunchMaya
#
# Environment:
#   DCC_MCP_CORE_REPO — override path to dcc-mcp-core (default: sibling of this git repo)
#
# Maya 2022 uses Python 3.7: pass -MayaVersion 2022 so mayapy builds cp37 extensions and the
# module layout uses python37/ + PYTHONPATH+:=python37 (matches dcc_mcp_maya_plugin path logic).
#
# Maya 2023+ mayapy is 3.8+: we pass abi3-py38 so maturin develop matches published wheels
# (_core.cp38-abi3-*.pyd). One build loads on 3.8–3.13 for that arch — avoids cp311 vs cp312
# mismatches when pytest uses a different interpreter than the mayapy that built core.

param(
    [string]$MayaVersion = "2025",
    [string]$CoreRepo = "",
    [switch]$SkipBuild,
    [switch]$LaunchMaya
)

$ErrorActionPreference = "Stop"

$MayaRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $MayaRoot) {
    $MayaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if (-not $CoreRepo) {
    if ($env:DCC_MCP_CORE_REPO) {
        $CoreRepo = $env:DCC_MCP_CORE_REPO
    } else {
        $sibling = Join-Path (Split-Path $MayaRoot -Parent) "dcc-mcp-core"
        if (Test-Path (Join-Path $sibling "Cargo.toml")) {
            $CoreRepo = $sibling
        }
    }
}
if (-not $CoreRepo -or -not (Test-Path (Join-Path $CoreRepo "Cargo.toml"))) {
    Write-Error "dcc-mcp-core not found. Clone it next to dcc-mcp-maya or set DCC_MCP_CORE_REPO / -CoreRepo."
}

$CoreRepo = (Resolve-Path $CoreRepo).Path
$Mayapy = "C:\Program Files\Autodesk\Maya${MayaVersion}\bin\mayapy.exe"
if (-not (Test-Path $Mayapy)) {
    Write-Error "mayapy not found: $Mayapy (install Maya $MayaVersion or pass a different -MayaVersion)"
}

$PyTag = & $Mayapy -c "import sys; print('%d.%d' % (sys.version_info[0], sys.version_info[1]))"
$PyDirName = if ($PyTag -eq "3.7") { "python37" } else { "python" }
Write-Host "   Detected mayapy Python $PyTag — module PYTHONPATH will use '$PyDirName/'" -ForegroundColor Gray

# OPT_FEATURES mirror dcc-mcp-core justfile; abi3-py38 matches [tool.maturin] / release wheels
# for mayapy 3.8+. PyO3 abi3-py38 is unsupported on 3.7 — use the same non-abi3 set as WHEEL_FEATURES_PY37.
$OptFeatures = "workflow,scheduler,prometheus,job-persist-sqlite"
if ($PyTag -eq "3.7") {
    $DevFeatures = "python-bindings,ext-module,$OptFeatures"
    Write-Host "   Features: DEV (no abi3 — Maya 2022 / Python 3.7)" -ForegroundColor Gray
} else {
    $DevFeatures = "python-bindings,ext-module,abi3-py38,$OptFeatures"
    Write-Host "   Features: DEV + abi3-py38 (stable ABI, same as PyPI wheel tag)" -ForegroundColor Gray
}

Write-Host "=== dcc-mcp-core (maturin develop via mayapy) ===" -ForegroundColor Cyan
Write-Host "   Core repo : $CoreRepo"
Write-Host "   Mayapy    : $Mayapy"
Write-Host ""

if (-not $SkipBuild) {
    Push-Location $CoreRepo
    try {
        Write-Host "   Running stub_gen (cargo)..." -ForegroundColor Gray
        & cargo run -q --bin stub_gen --features stub-gen
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   ⚠️  stub_gen failed (exit $LASTEXITCODE); continuing — run manually in core if needed" -ForegroundColor Yellow
        }

        & $Mayapy -m pip install -q --upgrade pip
        & $Mayapy -m pip install -q maturin

        $coreNativeDir = Join-Path $CoreRepo "python\dcc_mcp_core"
        Get-ChildItem -Path $coreNativeDir -Filter "_core*.pyd" -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "   Removing stale $($_.Name) before rebuild" -ForegroundColor Gray
            Remove-Item $_.FullName -Force
        }

        Write-Host "   maturin develop --features $DevFeatures ..." -ForegroundColor Gray
        & $Mayapy -m maturin develop --features $DevFeatures
        if ($LASTEXITCODE -ne 0) { throw "maturin develop failed" }

        # Build the standalone dcc-mcp-server binary for sidecar mode (RFC #998).
        # No mayapy involvement — this is a pure Rust binary. We reuse the same
        # target/ directory the maturin develop step just populated so cargo
        # finds most artefacts already compiled (link step only, ~5s on a warm
        # build).
        Write-Host "   cargo build --release -p dcc-mcp-server (sidecar binary) ..." -ForegroundColor Gray
        & cargo build --release -p dcc-mcp-server
        if ($LASTEXITCODE -ne 0) { throw "cargo build dcc-mcp-server failed" }
    } finally {
        Pop-Location
    }

    $corePkg = Join-Path $CoreRepo "python\dcc_mcp_core"
    if (-not (Test-Path $corePkg)) {
        Write-Error "Expected package dir missing after build: $corePkg"
    }
    Write-Host "   ✅ dcc_mcp_core built under $corePkg" -ForegroundColor Green
} else {
    Write-Host "   SkipBuild: not rebuilding core" -ForegroundColor Yellow
}

# Resolve the sidecar binary path produced by the build step above.
# We resolve it AFTER -SkipBuild handling so re-link runs can still
# wire the .mod file correctly when a prior build is reusable.
$ServerBin = Join-Path $CoreRepo "target\release\dcc-mcp-server.exe"
if (-not (Test-Path $ServerBin)) {
    Write-Host "   ⚠️  dcc-mcp-server.exe not found at $ServerBin" -ForegroundColor Yellow
    Write-Host "       Default sidecar mode will fall back to PATH lookup or fail." -ForegroundColor Yellow
    $ServerBin = $null
} else {
    Write-Host "   ✅ dcc-mcp-server binary at $ServerBin" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Maya module link (core + maya) ===" -ForegroundColor Cyan

$ModDir = Join-Path $env:USERPROFILE "Documents\maya\modules"
$Target = Join-Path $ModDir "dcc-mcp-maya"
$PkgMaya = Join-Path $MayaRoot "src\dcc_mcp_maya"
$PkgCore = Join-Path $CoreRepo "python\dcc_mcp_core"

if (-not (Test-Path $PkgMaya)) { Write-Error "Missing $PkgMaya" }
if (-not (Test-Path $PkgCore)) { Write-Error "Missing $PkgCore — build core first (remove -SkipBuild)" }

New-Item -ItemType Directory -Force -Path $ModDir | Out-Null
if (Test-Path $Target) {
    Remove-Item $Target -Recurse -Force
    Write-Host "   Removed old $Target" -ForegroundColor Gray
}

New-Item -ItemType Directory -Force -Path (Join-Path $Target $PyDirName) | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Target "plug-ins") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Target "scripts") | Out-Null

$pyDir = Join-Path $Target $PyDirName
$linkMaya = Join-Path $pyDir "dcc_mcp_maya"
$linkCore = Join-Path $pyDir "dcc_mcp_core"

try {
    New-Item -ItemType SymbolicLink -Path $linkMaya -Target $PkgMaya -ErrorAction Stop | Out-Null
    Write-Host "   ✅ $linkMaya → $PkgMaya" -ForegroundColor Green
} catch {
    Write-Error "Symlink dcc_mcp_maya failed (enable Windows Developer Mode or run elevated): $_"
}
try {
    New-Item -ItemType SymbolicLink -Path $linkCore -Target $PkgCore -ErrorAction Stop | Out-Null
    Write-Host "   ✅ $linkCore → $PkgCore" -ForegroundColor Green
} catch {
    Write-Error "Symlink dcc_mcp_core failed: $_"
}

Copy-Item -Path (Join-Path $MayaRoot "maya\plugin\dcc_mcp_maya_plugin.py") -Destination (Join-Path $Target "plug-ins") -Force
$UserSetupDest = Join-Path $Target "scripts\userSetup.py"
Copy-Item -Path (Join-Path $MayaRoot "maya\userSetup.py") -Destination $UserSetupDest -Force
Write-Host "   ✅ plug-ins + scripts copied" -ForegroundColor Green

# Dev-mode env-var defaults appended to userSetup.py (NOT to the .mod file).
#
# Why not the .mod file? Maya parses `.mod` files for module discovery and
# only reliably supports `:=` / `+:=` / `+=` for **path-list** variables
# (PYTHONPATH, MAYA_PLUG_IN_PATH, MAYA_SCRIPT_PATH). Plain env vars set via
# `KEY := value` are honoured by some Maya versions but silently ignored by
# others (verified Maya 2026: dcc-mcp-maya#244 — sidecar did not spawn even
# though the line was in the .mod file).
#
# `userSetup.py` runs Python code during Maya init and is honoured by every
# Maya version we target. Using ``os.environ.setdefault`` keeps any
# shell-level override the operator set before launching Maya (e.g.
# ``set DCC_MCP_MAYA_SIDECAR=0``).
#
# PyPI / production installs ship `maya/userSetup.py` unmodified — only
# this dev script appends the local binary path for live core builds.
if ($ServerBin) {
    $ServerBinEscaped = $ServerBin -replace '\\', '\\'
    $DevBlock = @"


# ── Dev-mode env defaults (appended by tools/maya-dev-build-link-core-win.ps1) ──
# NOT present in PyPI installs. Pins the sidecar binary path (RFC #998)
# so a fresh ``vx just maya-dev-build-link-core-win`` run uses the live
# core build when the default sidecar starts alongside Maya.
import os as _dcc_mcp_dev_os
_dcc_mcp_dev_os.environ.setdefault("DCC_MCP_SERVER_BIN", "$ServerBinEscaped")
"@
    Add-Content -Path $UserSetupDest -Value $DevBlock -Encoding UTF8
    Write-Host "   ✅ dev-mode env defaults appended to userSetup.py" -ForegroundColor Green
}

$ModContent = @(
    "+ dcc-mcp-maya 0.0.0-dev $Target",
    "PYTHONPATH+:=${PyDirName}",
    "MAYA_PLUG_IN_PATH+:=plug-ins",
    "MAYA_SCRIPT_PATH+:=scripts"
)
$ModFile = Join-Path $ModDir "dcc-mcp-maya.mod"
$ModContent | Out-File -FilePath $ModFile -Encoding ASCII
Write-Host "   ✅ $ModFile" -ForegroundColor Green

Write-Host ""
Write-Host "Done. Start Maya $MayaVersion — PYTHONPATH includes live dcc_mcp_core + dcc_mcp_maya." -ForegroundColor Cyan
Write-Host ""
Write-Host "MCP (Streamable HTTP, default per-Maya):" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:8765/mcp"
Write-Host "MCP via elected gateway (multi-instance, if enabled):" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:9765/mcp"
Write-Host "Docs: docs/guide/local-mcp-debug.md | examples/mcp/cursor-maya-streamable-http.json" -ForegroundColor Gray

if ($ServerBin) {
    Write-Host ""
    Write-Host "Sidecar mode (experimental, RFC #998) — enabled by default:" -ForegroundColor Cyan
    Write-Host "   The dev script appended ``os.environ.setdefault`` calls to the" -ForegroundColor Gray
    Write-Host "   shipped userSetup.py so the live sidecar binary path is set" -ForegroundColor Gray
    Write-Host "   the moment Maya boots Python. Just launch Maya." -ForegroundColor Gray
    Write-Host "   Verify in Task Manager — a 'dcc-mcp-server.exe' child should" -ForegroundColor Gray
    Write-Host "   appear under Maya within a second of plug-in init." -ForegroundColor Gray
    Write-Host "   To test legacy in-process-only, run with DCC_MCP_MAYA_SIDECAR=0" -ForegroundColor Gray
    Write-Host "   in the launching shell (the ``setdefault`` honours that)." -ForegroundColor Gray
}

if ($LaunchMaya) {
    $mayaExe = "C:\Program Files\Autodesk\Maya${MayaVersion}\bin\maya.exe"
    if (-not (Test-Path $mayaExe)) {
        Write-Error "Maya executable not found: $mayaExe"
    }
    Write-Host "Launching $mayaExe ..." -ForegroundColor Cyan
    Start-Process -FilePath $mayaExe
}
