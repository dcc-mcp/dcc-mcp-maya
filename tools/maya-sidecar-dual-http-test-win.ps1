# HTTP smoke test for two (or more) Maya instances behind per-DCC sidecars (Windows).
#
# REST /v1/* is served by each Maya in-process MCP listener (FileRegistry rows with
# dcc_type=maya). Sidecar processes expose /mcp only; this script reports their ports
# for correlation but does not call sidecar /mcp (use gateway or per-DCC REST).
#
# Prerequisites: at least one live Maya with dcc-mcp-maya + sidecar supervisor running.
#
# Usage:
#   .\tools\maya-sidecar-dual-http-test-win.ps1
#   .\tools\maya-sidecar-dual-http-test-win.ps1 -SearchQuery get_session_info
#     (requires a Maya build with the cmds.ls boolean-flag worker-thread fix)
#   .\tools\maya-sidecar-dual-http-test-win.ps1 -SearchQuery execute_python
#   .\tools\maya-sidecar-dual-http-test-win.ps1 -IncludeGateway
#   .\tools\maya-sidecar-dual-http-test-win.ps1 -BaseUrl http://127.0.0.1:50968
#
# Environment:
#   DCC_MCP_REGISTRY_DIR — override registry directory (default: %TEMP%\dcc-mcp-registry)

param(
    [string]$RegistryDir = "",
    [int]$GatewayPort = 9765,
    [string]$SearchQuery = "execute_python",
    [string]$BaseUrl = "",
    [switch]$IncludeGateway,
    [switch]$SkipCall,
    [switch]$UseExecutePython,
    [switch]$PassThru
)

$ErrorActionPreference = "Stop"

function Resolve-RegistryDir {
    param([string]$Override)
    if ($Override) { return $Override }
    if ($env:DCC_MCP_REGISTRY_DIR) { return $env:DCC_MCP_REGISTRY_DIR }
    return Join-Path $env:TEMP "dcc-mcp-registry"
}

function Read-RegistryEntries {
    param([string]$Dir)
    $path = Join-Path $Dir "services.json"
    if (-not (Test-Path $path)) {
        throw "Registry not found: $path (start Maya + dcc-mcp-maya first)"
    }
    $raw = Get-Content -Path $path -Raw -Encoding UTF8
    $payload = $raw | ConvertFrom-Json
    if ($payload -is [System.Array]) {
        return @($payload)
    }
    if ($payload.services) {
        return @($payload.services)
    }
    return @()
}

function Get-MetadataValue {
    param($Entry, [string]$Key)
    if (-not $Entry.metadata) { return $null }
    if ($Entry.metadata -is [hashtable]) {
        return $Entry.metadata[$Key]
    }
    $prop = $Entry.metadata.PSObject.Properties[$Key]
    if ($prop) { return $prop.Value }
    return $null
}

function Test-TcpListening {
    param([string]$HostName = "127.0.0.1", [int]$Port)
    if ($Port -le 0) { return $false }
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(500)
        if ($ok -and $client.Connected) {
            $client.EndConnect($iar)
            $client.Close()
            return $true
        }
        $client.Close()
    } catch {
        # not listening
    }
    return $false
}

function Invoke-RestJson {
    param(
        [string]$Method,
        [string]$Url,
        $Body = $null,
        [int]$TimeoutSec = 120
    )
    $params = @{
        Uri             = $Url
        Method          = $Method
        TimeoutSec      = $TimeoutSec
        UseBasicParsing = $true
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        if ($Body -is [string]) {
            $params.Body = $Body
        } else {
            $params.Body = ($Body | ConvertTo-Json -Depth 12 -Compress)
        }
    }
    $response = Invoke-WebRequest @params
    if (-not $response.Content) { return $null }
    return $response.Content | ConvertFrom-Json
}

function Get-ToolSlugFromHit {
    param($Hit)
    if ($Hit.tool_slug) { return $Hit.tool_slug }
    if ($Hit.slug) { return $Hit.slug }
    return $null
}

function Discover-MayaRestTargets {
    param([string]$Dir)

    $entries = Read-RegistryEntries -Dir $Dir
    $sidecars = @{}
    foreach ($e in $entries) {
        $role = Get-MetadataValue -Entry $e -Key "dcc_mcp_role"
        if ($role -eq "per-dcc-sidecar" -and $e.pid) {
            $sidecars[[int]$e.pid] = $e
        }
    }

    $targets = @()
    foreach ($e in $entries) {
        if ($e.dcc_type -ne "maya") { continue }
        $hostAddr = if ($e.host) { $e.host } else { "127.0.0.1" }
        $port = [int]$e.port
        if (-not (Test-TcpListening -HostName $hostAddr -Port $port)) { continue }

        $base = "http://${hostAddr}:$port"
        try {
            $hz = Invoke-RestJson -Method GET -Url "$base/v1/healthz" -TimeoutSec 5
            if (-not $hz -or $hz.ok -ne $true) { continue }
        } catch {
            continue
        }

        $sidecar = $null
        $watchPid = [int]$e.pid
        if ($sidecars.ContainsKey($watchPid)) {
            $sidecar = $sidecars[$watchPid]
        }

        $label = if ($e.display_name) { $e.display_name }
        elseif ($e.version) { "Maya $($e.version) pid=$watchPid" }
        else { "Maya pid=$watchPid" }

        $sidecarUrl = $null
        if ($sidecar) {
            $sh = if ($sidecar.host) { $sidecar.host } else { "127.0.0.1" }
            $sp = [int]$sidecar.port
            $metaUrl = Get-MetadataValue -Entry $sidecar -Key "mcp_url"
            if ($metaUrl) {
                $sidecarUrl = $metaUrl
            } elseif ($sp -gt 0 -and (Test-TcpListening -HostName $sh -Port $sp)) {
                $sidecarUrl = "http://${sh}:$sp/mcp"
            }
        }

        $targets += [pscustomobject]@{
            Label       = $label
            BaseUrl     = $base
            Pid         = $watchPid
            Port        = $port
            Version     = $e.version
            InstanceId  = $e.instance_id
            SidecarUrl  = $sidecarUrl
            HostRpcUri  = if ($sidecar) { Get-MetadataValue -Entry $sidecar -Key "host_rpc_uri" } else { $null }
        }
    }

    return $targets | Sort-Object Port
}

function Test-MayaRestInstance {
    param(
        $Target,
        [string]$Query,
        [switch]$NoCall,
        [switch]$PythonCall
    )

    $base = $Target.BaseUrl
    $results = [ordered]@{
        label   = $Target.Label
        baseUrl = $base
        steps   = @()
        ok      = $true
    }

    function Add-Step {
        param([string]$Name, [bool]$Success, [string]$Detail)
        $results.steps += [pscustomobject]@{ name = $Name; ok = $Success; detail = $Detail }
        if (-not $Success) { $results.ok = $false }
    }

    try {
        $hz = Invoke-RestJson -Method GET -Url "$base/v1/healthz" -TimeoutSec 10
        Add-Step "healthz" ($hz.ok -eq $true) ("ok=$($hz.ok)")
    } catch {
        Add-Step "healthz" $false $_.Exception.Message
        return $results
    }

    try {
        $rz = Invoke-RestJson -Method GET -Url "$base/v1/readyz" -TimeoutSec 10
        $detail = if ($rz.process -ne $null) {
            "process=$($rz.process) dispatcher=$($rz.dispatcher) dcc=$($rz.dcc)"
        } else {
            ($rz | ConvertTo-Json -Compress)
        }
        Add-Step "readyz" $true $detail
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 503) {
            Add-Step "readyz" $true "503 not-ready (booting): $($_.Exception.Message)"
        } else {
            Add-Step "readyz" $false $_.Exception.Message
        }
    }

  try {
        $searchBody = @{ query = $Query; limit = 8 }
        if ($Target.dcc_type) { $searchBody.dcc_type = "maya" }
        $search = Invoke-RestJson -Method POST -Url "$base/v1/search" -Body $searchBody
        $total = if ($null -ne $search.total) { [int]$search.total } else { @($search.hits).Count }
        Add-Step "search" ($total -gt 0) "total=$total query=$Query"

        if ($total -le 0) { return $results }

        $hit = $null
        foreach ($h in $search.hits) {
            $action = "$($h.action)"
            if ($PythonCall) {
                if ($action -match "execute_python") { $hit = $h; break }
            } elseif ($action -match [regex]::Escape($Query.Replace(" ", "_")) -or $action -match $Query.Replace("-", "_")) {
                $hit = $h; break
            }
        }
        if (-not $hit) { $hit = $search.hits[0] }

        $slug = Get-ToolSlugFromHit -Hit $hit
        if (-not $slug) {
            Add-Step "resolve_slug" $false "first hit has no slug/tool_slug"
            return $results
        }
        Add-Step "resolve_slug" $true $slug

        $desc = Invoke-RestJson -Method POST -Url "$base/v1/describe" -Body @{ tool_slug = $slug }
        $hasSchema = $desc.record.has_schema
        Add-Step "describe" $true "has_schema=$hasSchema action=$($desc.record.backend_tool)"

        if ($NoCall) {
            Add-Step "call" $true "skipped (-SkipCall)"
            return $results
        }

        if ($PythonCall -or ($hit.action -match "execute_python")) {
            $callArgs = @{
                code = @"
import maya.cmds as cmds
print('SIDECAR_HTTP_TEST', cmds.about(version=True))
"@
            }
        } else {
            $callArgs = @{}
        }

        $call = Invoke-RestJson -Method POST -Url "$base/v1/call" -Body @{
            tool_slug = $slug
            arguments = $callArgs
        } -TimeoutSec 120

        $success = $call.output.success -eq $true
        $msg = $call.output.message
        if ($call.output.context.stdout) {
            $msg = "$msg | stdout=$($call.output.context.stdout.Trim())"
        }
        Add-Step "call" $success $msg
    } catch {
        Add-Step "search_or_call" $false $_.Exception.Message
    }

    return $results
}

function Test-GatewayRest {
    param([int]$Port, [string]$Query)

    $base = "http://127.0.0.1:$Port"
    if (-not (Test-TcpListening -Port $Port)) {
        return [pscustomobject]@{
            label = "gateway"
            baseUrl = $base
            ok = $false
            steps = @([pscustomobject]@{ name = "listen"; ok = $false; detail = "port not listening" })
        }
    }

    $results = [ordered]@{
        label   = "gateway :$Port"
        baseUrl = $base
        steps   = @()
        ok      = $true
    }

    function Add-GwStep {
        param([string]$Name, [bool]$Success, [string]$Detail)
        $results.steps += [pscustomobject]@{ name = $Name; ok = $Success; detail = $Detail }
        if (-not $Success) { $results.ok = $false }
    }

    try {
        $hz = Invoke-RestJson -Method GET -Url "$base/v1/healthz" -TimeoutSec 5
        Add-GwStep "healthz" ($hz.ok -eq $true) "ok=$($hz.ok)"
    } catch {
        Add-GwStep "healthz" $false $_.Exception.Message
        return [pscustomobject]$results
    }

    try {
        $inst = Invoke-RestJson -Method GET -Url "$base/v1/instances" -TimeoutSec 10
        $count = if ($inst.instances) { @($inst.instances).Count } else { 0 }
        Add-GwStep "instances" $true "count=$count"
    } catch {
        Add-GwStep "instances" $false $_.Exception.Message
    }

    try {
        $search = Invoke-RestJson -Method POST -Url "$base/v1/search" -Body @{
            query    = $Query
            dcc_type = "maya"
            limit    = 5
        }
        $total = if ($null -ne $search.total) { [int]$search.total } else { 0 }
        $hasSlug = ($search.hits | Where-Object { $_.tool_slug -or $_.slug }).Count -gt 0
        Add-GwStep "search" ($total -gt 0 -and $hasSlug) "total=$total"
    } catch {
        Add-GwStep "search" $false $_.Exception.Message
    }

    return [pscustomobject]$results
}

# --- main ---

$regDir = Resolve-RegistryDir -Override $RegistryDir
Write-Host "Maya sidecar dual-instance HTTP test" -ForegroundColor Cyan
Write-Host "  Registry: $regDir"
Write-Host "  Search:   $SearchQuery"
Write-Host ""

$allResults = @()

if ($BaseUrl) {
    $targets = @([pscustomobject]@{
        Label      = "manual"
        BaseUrl    = $BaseUrl.TrimEnd("/")
        Pid        = 0
        Port       = 0
        Version    = ""
        InstanceId = ""
        SidecarUrl = $null
        HostRpcUri = $null
    })
} else {
    $targets = Discover-MayaRestTargets -Dir $regDir
}

if ($targets.Count -eq 0) {
    Write-Host "No live Maya REST listeners found (dcc_type=maya with /v1/healthz)." -ForegroundColor Red
    Write-Host "  - Confirm Maya is running with dcc-mcp-maya plugin loaded." -ForegroundColor Yellow
    Write-Host "  - Sidecar alone does not serve /v1/*; the in-process MCP port is required." -ForegroundColor Yellow
    exit 1
}

Write-Host "Discovered $($targets.Count) Maya REST endpoint(s):" -ForegroundColor Green
foreach ($t in $targets) {
    Write-Host "  [$($t.Label)] $($t.BaseUrl)  instance=$($t.InstanceId)"
    if ($t.SidecarUrl) {
        Write-Host "    sidecar MCP: $($t.SidecarUrl)" -ForegroundColor DarkGray
    }
    if ($t.HostRpcUri) {
        Write-Host "    host RPC:    $($t.HostRpcUri)" -ForegroundColor DarkGray
    }
}
Write-Host ""

# execute_python needs a code payload; other tools use empty arguments.
$usePython = $UseExecutePython -or ($SearchQuery -match "execute_python")
foreach ($t in $targets) {
    Write-Host "--- $($t.Label) @ $($t.BaseUrl) ---" -ForegroundColor Cyan
    $r = Test-MayaRestInstance -Target $t -Query $SearchQuery -NoCall:$SkipCall -PythonCall:$usePython
    $allResults += [pscustomobject]$r
    foreach ($step in $r.steps) {
        $color = if ($step.ok) { "Green" } else { "Red" }
        $mark = if ($step.ok) { "OK" } else { "FAIL" }
        Write-Host "  [$mark] $($step.name): $($step.detail)" -ForegroundColor $color
    }
    Write-Host ""
}

if ($IncludeGateway) {
    Write-Host "--- Gateway ---" -ForegroundColor Cyan
    $gw = Test-GatewayRest -Port $GatewayPort -Query $SearchQuery
    $allResults += $gw
    foreach ($step in $gw.steps) {
        $color = if ($step.ok) { "Green" } else { "Red" }
        $mark = if ($step.ok) { "OK" } else { "FAIL" }
        Write-Host "  [$mark] $($step.name): $($step.detail)" -ForegroundColor $color
    }
    Write-Host ""
}

$failed = @($allResults | Where-Object { -not $_.ok })
if ($failed.Count -eq 0) {
    Write-Host "All $($allResults.Count) target(s) passed." -ForegroundColor Green
    if ($PassThru) { return $allResults }
    exit 0
}

Write-Host "$($failed.Count) target(s) failed." -ForegroundColor Red
if ($PassThru) { return $allResults }
exit 1
