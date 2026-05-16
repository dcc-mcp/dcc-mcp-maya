# maya-mcp-style inline execute_python (no file_path) — 10 spheres + C:/test.fbx
# Uses executeInMainThreadWithResult inside the snippet (same as batch_spheres_to_test_fbx.py).

param(
    [string]$BaseUrl = "",
    [string]$FbxPath = "C:/test.fbx"
)

$ErrorActionPreference = "Stop"

if (-not $BaseUrl) {
    $reg = Join-Path $env:TEMP "dcc-mcp-registry"
    $entry = Get-Content (Join-Path $reg "services.json") -Raw | ConvertFrom-Json |
        Where-Object { $_.dcc_type -eq "maya" } | Select-Object -First 1
    if (-not $entry) { throw "No Maya in registry" }
    $BaseUrl = "http://$($entry.host):$($entry.port)"
}

$code = @"
import random
import maya.cmds as cmds
import maya.mel as mel
import maya.utils as utils

FBX = "$($FbxPath -replace '\\','/')"

def work():
    created = []
    for i in range(10):
        n, _ = cmds.polySphere(radius=random.uniform(0.2, 0.5), name='mcp_sphere_%02d' % (i+1))
        cmds.move(random.uniform(-5,5), random.uniform(0,3), random.uniform(-5,5), n)
        created.append(n)
    g = cmds.group(created, name='mcp_sphere_grp')
    cmds.select(g, replace=True)
    if not cmds.pluginInfo('fbxmaya', query=True, loaded=True):
        cmds.loadPlugin('fbxmaya')
    mel.eval('FBXResetExport')
    cmds.file(FBX, force=True, options='v=0;', type='FBX export', exportSelected=True)
    import os
    return 'INLINE_OK fbx=%s bytes=%s' % (FBX, os.path.getsize(FBX))

print(utils.executeInMainThreadWithResult(work))
"@

$search = Invoke-RestMethod "$BaseUrl/v1/search" -Method POST -ContentType "application/json" `
    -Body '{"query":"execute_python","limit":5}'
$slug = ($search.hits | Where-Object { $_.action -match 'execute_python' }).slug
if (-not $slug) { throw "execute_python not found" }

Write-Host "Base: $BaseUrl" -ForegroundColor Cyan
Write-Host "FBX:  $FbxPath" -ForegroundColor Cyan

$body = @{
    tool_slug = $slug
    arguments = @{
        code           = $code
        capture_output = $true
        result_type    = "NONE"
    }
} | ConvertTo-Json -Depth 6

$r = Invoke-RestMethod "$BaseUrl/v1/call" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 300
Write-Host "success=$($r.output.success)"
Write-Host $r.output.context.stdout
if (-not $r.output.success) { $r.output | ConvertTo-Json -Depth 6; exit 1 }
if (Test-Path $FbxPath) { Get-Item $FbxPath | Format-List FullName, Length, LastWriteTime }
