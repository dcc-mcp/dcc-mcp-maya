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

# Same feature set as dcc-mcp-core justfile DEV_FEATURES (keep in sync when OPT_FEATURES changes).
$DevFeatures = "python-bindings,ext-module,workflow,scheduler,prometheus,job-persist-sqlite"

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

        Write-Host "   maturin develop --features $DevFeatures ..." -ForegroundColor Gray
        & $Mayapy -m maturin develop --features $DevFeatures
        if ($LASTEXITCODE -ne 0) { throw "maturin develop failed" }
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
Copy-Item -Path (Join-Path $MayaRoot "maya\userSetup.py") -Destination (Join-Path $Target "scripts") -Force
Write-Host "   ✅ plug-ins + scripts copied" -ForegroundColor Green

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

if ($LaunchMaya) {
    $mayaExe = "C:\Program Files\Autodesk\Maya${MayaVersion}\bin\maya.exe"
    if (-not (Test-Path $mayaExe)) {
        Write-Error "Maya executable not found: $mayaExe"
    }
    Write-Host "Launching $mayaExe ..." -ForegroundColor Cyan
    Start-Process -FilePath $mayaExe
}
