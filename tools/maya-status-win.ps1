# Maya dev link status for Windows (PowerShell)
# This script shows the status of Maya dev symlinks

$ModDir = Join-Path $env:USERPROFILE "Documents\maya\modules"
$Target = Join-Path $ModDir "dcc-mcp-maya"
$ModFile = Join-Path $ModDir "dcc-mcp-maya.mod"

Write-Host "📋 Maya dev link status:" -ForegroundColor Cyan
Write-Host "   Modules dir: $ModDir"
Write-Host ""

# Check python directory
$PythonPath = Join-Path $Target "python"
if (Test-Path $PythonPath) {
    $Item = Get-Item $PythonPath
    if ($Item.LinkType -eq 'SymbolicLink') {
        Write-Host "   ✅ python/   → $($Item.Target) (symlink)" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  python/   exists (copied, not linked)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ❌ python/   not found" -ForegroundColor Red
}

# Check plug-ins
$PluginPath = Join-Path $Target "plug-ins\dcc_mcp_maya_plugin.py"
if (Test-Path $PluginPath) {
    $Item = Get-Item $PluginPath
    if ($Item.LinkType -eq 'SymbolicLink') {
        Write-Host "   ✅ plug-ins/ → linked" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  plug-ins/ exists (copied)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ❌ plug-ins/ not found" -ForegroundColor Red
}

# Check .mod file
if (Test-Path $ModFile) {
    Write-Host "   ✅ .mod file  exists" -ForegroundColor Green
} else {
    Write-Host "   ❌ .mod file  not found" -ForegroundColor Red
}
