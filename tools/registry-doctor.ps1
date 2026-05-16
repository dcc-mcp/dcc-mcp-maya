# Inspect + optionally clean both FileRegistry directories used by
# dcc-mcp (Maya in-process + sidecar binary). Diagnoses the split-brain
# scenario described in RFC #998 follow-up (2026-05-16): the Rust
# sidecar binary used to default to a different temp subdir than the
# Maya in-process GatewayRunner, so gateway competition went split-brain.
#
# After the Maya plug-in fix (commit a6e4dea7), new sidecars use the
# same dir as in-process. This script helps clean up leftovers and
# verify the unified view going forward.
#
# Usage:
#   .\tools\registry-doctor.ps1                  # inspect only
#   .\tools\registry-doctor.ps1 -Clean           # remove stale-pid + ghost rows
#   .\tools\registry-doctor.ps1 -Nuke            # delete both registry files entirely (use after all DCC sessions closed)

param(
    [switch]$Clean,
    [switch]$Nuke
)

$ErrorActionPreference = "Stop"

$temp = $env:TEMP
$paths = @(
    @{Label = "GatewayRunner / Maya in-process (canonical)"; Path = "$temp\dcc-mcp-registry\services.json"}
    @{Label = "Sidecar default (split-brain, pre-fix)"; Path = "$temp\dcc-mcp\registry\services.json"}
)

function Test-PidAlive([int]$ProcessId) {
    if ($ProcessId -le 0) { return $false }
    try {
        $null = Get-Process -Id $ProcessId -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

foreach ($entry in $paths) {
    $p = $entry.Path
    Write-Output "=== $($entry.Label) ==="
    Write-Output "  Path: $p"
    if (-not (Test-Path $p)) {
        Write-Output "  (file does not exist)"
        Write-Output ""
        continue
    }

    $raw = Get-Content $p -Raw
    try {
        $rows = $raw | ConvertFrom-Json
    } catch {
        Write-Output "  Cannot parse JSON: $($_.Exception.Message)"
        Write-Output ""
        continue
    }

    if ($rows.Count -eq 0) {
        Write-Output "  (empty)"
        Write-Output ""
        continue
    }

    $alive = @()
    $dead = @()
    foreach ($r in $rows) {
        if (Test-PidAlive $r.pid) { $alive += $r } else { $dead += $r }
    }

    Write-Output ("  Total: {0}  Alive: {1}  Dead: {2}" -f $rows.Count, $alive.Count, $dead.Count)
    if ($alive.Count -gt 0) {
        Write-Output "  --- alive ---"
        $alive | ForEach-Object {
            Write-Output ("    {0,-14} :{1,-5} pid={2,-7} ver={3}" -f $_.dcc_type, $_.port, $_.pid, $_.version)
        }
    }
    if ($dead.Count -gt 0) {
        Write-Output "  --- DEAD (owning pid is gone) ---"
        $dead | ForEach-Object {
            Write-Output ("    {0,-14} :{1,-5} pid={2,-7} ver={3}" -f $_.dcc_type, $_.port, $_.pid, $_.version)
        }
    }

    if ($Clean -and $dead.Count -gt 0) {
        Write-Output "  -> cleaning $($dead.Count) dead row(s)..."
        $alive | ConvertTo-Json -Depth 8 | Set-Content -Path $p -Encoding UTF8
        Write-Output "  -> done"
    }

    Write-Output ""
}

if ($Nuke) {
    Write-Output ""
    Write-Output "=== NUKE both registry files ==="
    foreach ($entry in $paths) {
        $p = $entry.Path
        if (Test-Path $p) {
            Remove-Item $p -Force
            Write-Output "  removed: $p"
        }
    }
    Write-Output ""
    Write-Output "Also wiping sentinel lock dirs..."
    foreach ($lock_dir in @("$temp\dcc-mcp-registry\locks", "$temp\dcc-mcp\registry\locks")) {
        if (Test-Path $lock_dir) {
            Get-ChildItem $lock_dir -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
            Write-Output "  cleared: $lock_dir"
        }
    }
}

Write-Output ""
Write-Output "=== 9765 status ==="
$g = Get-NetTCPConnection -LocalPort 9765 -State Listen -ErrorAction SilentlyContinue
if ($g) {
    foreach ($c in $g) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        Write-Output ("  LISTENING  pid={0} name={1}" -f $c.OwningProcess, $proc.ProcessName)
    }
} else {
    Write-Output "  no listener on 9765"
}
