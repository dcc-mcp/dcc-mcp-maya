# Maya dev symlinks setup for Windows (PowerShell)
# This script creates symlinks from source tree into Maya's module directory

param(
    [string]$MayaVersion = "2025"
)

# Find project root (where .git directory is)
$ProjectRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $ProjectRoot) {
    # Fallback: assume script is in tools/ subdirectory
    $ProjectRoot = $PSScriptRoot | Split-Path | Split-Path
}
$ModDir = Join-Path $env:USERPROFILE "Documents\maya\modules"
$Target = Join-Path $ModDir "dcc-mcp-maya"

Write-Host "🔗 Setting up Maya dev symlinks (Maya $MayaVersion)..." -ForegroundColor Cyan
Write-Host "   Project  : $ProjectRoot" -ForegroundColor Gray
Write-Host "   Module   : $Target" -ForegroundColor Gray
Write-Host ""

# Create modules dir if needed
New-Item -ItemType Directory -Force -Path $ModDir | Out-Null

# Remove old link/dir if exists
if (Test-Path $Target) {
    Remove-Item $Target -Recurse -Force
    Write-Host "   Removed old directory/link"
}

# Create module directory structure
New-Item -ItemType Directory -Force -Path (Join-Path $Target "plug-ins") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Target "scripts") | Out-Null

# Create symbolic links (requires developer mode or admin)
try {
    # Symlink python directory
    New-Item -ItemType SymbolicLink -Path (Join-Path $Target "python") -Target (Join-Path $ProjectRoot "src") -ErrorAction Stop
    Write-Host "   ✅ Created symlink: python/ → src/" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Symlink failed, copying instead..." -ForegroundColor Yellow
    Copy-Item -Path (Join-Path $ProjectRoot "src") -Destination (Join-Path $Target "python") -Recurse
}

# Copy plugin file
Copy-Item -Path (Join-Path $ProjectRoot "maya\plugin\dcc_mcp_maya_plugin.py") -Destination (Join-Path $Target "plug-ins") -Force
Write-Host "   ✅ Copied: plug-ins/dcc_mcp_maya_plugin.py" -ForegroundColor Green

# Copy userSetup.py
Copy-Item -Path (Join-Path $ProjectRoot "maya\userSetup.py") -Destination (Join-Path $Target "scripts") -Force
Write-Host "   ✅ Copied: scripts/userSetup.py" -ForegroundColor Green

# Generate .mod file
$ModContent = @(
    "+ dcc-mcp-maya 0.0.0-dev $Target",
    "PYTHONPATH+:=python",
    "MAYA_PLUG_IN_PATH+:=plug-ins",
    "MAYA_SCRIPT_PATH+:=scripts"
)
$ModContent | Out-File -FilePath (Join-Path $ModDir "dcc-mcp-maya.mod") -Encoding ASCII

Write-Host ""
Write-Host "   ✅ Setup complete:" -ForegroundColor Green
Write-Host "      python/     → src/ (live source)"
Write-Host "      plug-ins/   → maya/plugin/"
Write-Host "      scripts/    → maya/userSetup.py"
Write-Host "      .mod file   → $(Join-Path $ModDir 'dcc-mcp-maya.mod')"
Write-Host ""
Write-Host "   Next: start Maya $MayaVersion — the plugin loads automatically." -ForegroundColor Cyan
Write-Host "   Edit source → restart Maya (or use hot-reload) to see changes." -ForegroundColor Cyan
