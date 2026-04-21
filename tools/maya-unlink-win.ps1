# Maya dev symlinks removal for Windows (PowerShell)
# This script removes symlinks and .mod file from Maya's module directory

$ModDir = Join-Path $env:USERPROFILE "Documents\maya\modules"
$Target = Join-Path $ModDir "dcc-mcp-maya"
$ModFile = Join-Path $ModDir "dcc-mcp-maya.mod"

Write-Host "🧹 Removing Maya dev symlinks..." -ForegroundColor Cyan

if (Test-Path $Target) {
    Remove-Item $Target -Recurse -Force
    Write-Host "   Removed $Target" -ForegroundColor Green
}
if (Test-Path $ModFile) {
    Remove-Item $ModFile -Force
    Write-Host "   Removed $ModFile" -ForegroundColor Green
}

Write-Host "   ✅ Dev symlinks cleaned up" -ForegroundColor Green
