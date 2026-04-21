# Install dcc-mcp-core into Maya's Python (Windows)
# This script finds mayapy.exe and installs dcc-mcp-core

param(
    [string]$MayaVersion = "2025"
)

# Try to find mayapy.exe in common installation paths
$CommonPaths = @(
    "C:\Program Files\Autodesk\Maya$MayaVersion\bin\mayapy.exe",
    "C:\Program Files\Autodesk\Maya$MayaVersion.1\bin\mayapy.exe",
    "C:\Program Files\Autodesk\Maya$MayaVersion.2\bin\mayapy.exe"
)

$MayapyPath = $null
foreach ($Path in $CommonPaths) {
    if (Test-Path $Path) {
        $MayapyPath = $Path
        break
    }
}

if (-not $MayapyPath) {
    # Try to find mayapy in PATH
    try {
        $MayapyPath = (Get-Command mayapy -ErrorAction Stop).Source
    } catch {
        Write-Host "❌ Error: mayapy not found in PATH or common installation paths" -ForegroundColor Red
        Write-Host "   Please specify Maya version or ensure mayapy is in PATH" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "📦 Installing dcc-mcp-core into Maya Python..." -ForegroundColor Cyan
Write-Host "   Using: $MayapyPath" -ForegroundColor Gray

& $MayapyPath -m pip install dcc-mcp-core --upgrade

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ dcc-mcp-core installed into Maya Python" -ForegroundColor Green
} else {
    Write-Host "❌ Installation failed" -ForegroundColor Red
    exit 1
}
