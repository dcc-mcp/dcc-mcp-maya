# Run a .py script file on every live Maya REST endpoint via execute_python + file_path.
#
# Scripts that call FBX export or loadPlugin must use maya.utils.executeInMainThreadWithResult
# inside the .py file (see batch_spheres_to_test_fbx.py). Otherwise Maya may crash when
# execute_python runs off the UI thread.
#
# Usage:
#   .\tools\maya-run-script-http-win.ps1 -ScriptPath .\tools\batch_random_spheres_smoke.py
#   .\tools\maya-run-script-http-win.ps1 -ScriptPath .\tools\batch_random_spheres_smoke.py -BaseUrl http://127.0.0.1:54742

param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,
    [string]$BaseUrl = "",
    [string]$RegistryDir = ""
)

$ErrorActionPreference = "Stop"

$scriptFull = (Resolve-Path $ScriptPath).Path
if (-not (Test-Path $scriptFull)) {
    throw "Script not found: $ScriptPath"
}
# Maya accepts forward slashes on Windows.
$mayaPath = $scriptFull -replace '\\', '/'

function Resolve-RegistryDir {
    param([string]$Override)
    if ($Override) { return $Override }
    if ($env:DCC_MCP_REGISTRY_DIR) { return $env:DCC_MCP_REGISTRY_DIR }
    return Join-Path $env:TEMP "dcc-mcp-registry"
}

function Read-MayaRestBases {
    param([string]$Dir)
    $path = Join-Path $Dir "services.json"
    if (-not (Test-Path $path)) { throw "No registry: $path" }
    $entries = Get-Content $path -Raw | ConvertFrom-Json
    $bases = @()
    foreach ($e in $entries) {
        if ($e.dcc_type -ne "maya") { continue }
        $hostAddr = if ($e.host) { $e.host } else { "127.0.0.1" }
        $port = [int]$e.port
        $base = "http://${hostAddr}:$port"
        try {
            $hz = Invoke-RestMethod "$base/v1/healthz" -TimeoutSec 5
            if ($hz.ok -eq $true) {
                $label = if ($e.display_name) { $e.display_name } else { "Maya $($e.version) pid=$($e.pid)" }
                $bases += [pscustomobject]@{ Label = $label; BaseUrl = $base }
            }
        } catch { }
    }
    return $bases | Sort-Object BaseUrl -Unique
}

function Get-ExecutePythonSlug {
    param([string]$Base)
    $search = Invoke-RestMethod "$Base/v1/search" -Method POST `
        -ContentType "application/json" `
        -Body (@{ query = "execute_python"; limit = 5 } | ConvertTo-Json)
    foreach ($h in $search.hits) {
        if ("$($h.action)" -match "execute_python") {
            if ($h.tool_slug) { return $h.tool_slug }
            if ($h.slug) { return $h.slug }
        }
    }
    throw "execute_python not found on $Base"
}

function Invoke-ScriptOnMaya {
    param([string]$Base, [string]$Label, [string]$Slug, [string]$FilePath)
    Write-Host "--- $Label @ $Base ---" -ForegroundColor Cyan
    $body = @{
        tool_slug = $Slug
        arguments = @{
            file_path    = $FilePath
            capture_output = $true
            result_type  = "NONE"
        }
    } | ConvertTo-Json -Depth 5
    $r = Invoke-RestMethod "$Base/v1/call" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 180
    $out = $r.output
    if ($out.success -ne $true) {
        Write-Host "  FAIL: $($out.message)" -ForegroundColor Red
        if ($out.context.stderr) { Write-Host $out.context.stderr }
        if ($out.context.traceback) { Write-Host $out.context.traceback }
        return $false
    }
    $stdout = ""
    if ($out.context.stdout) { $stdout = $out.context.stdout.Trim() }
    elseif ($out.context.output) { $stdout = "$($out.context.output)".Trim() }
    Write-Host "  OK: $($out.message)" -ForegroundColor Green
    if ($stdout) { Write-Host "  stdout: $stdout" }
    return $true
}

Write-Host "Running script: $mayaPath" -ForegroundColor Cyan

if ($BaseUrl) {
    $targets = @([pscustomobject]@{ Label = "manual"; BaseUrl = $BaseUrl.TrimEnd("/") })
} else {
    $targets = Read-MayaRestBases -Dir (Resolve-RegistryDir -Override $RegistryDir)
}

if ($targets.Count -eq 0) { throw "No live Maya REST endpoints" }

$ok = 0
foreach ($t in $targets) {
    $slug = Get-ExecutePythonSlug -Base $t.BaseUrl
    if (Invoke-ScriptOnMaya -Base $t.BaseUrl -Label $t.Label -Slug $slug -FilePath $mayaPath) {
        $ok++
    }
}

Write-Host ""
if ($ok -eq $targets.Count) {
    Write-Host "Script ran on $ok/$($targets.Count) instance(s)." -ForegroundColor Green
    exit 0
}
Write-Host "Script failed on $($targets.Count - $ok) instance(s)." -ForegroundColor Red
exit 1
