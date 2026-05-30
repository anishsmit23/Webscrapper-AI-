$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$port = 8015
while ($true) {
    $inUse = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $port -ErrorAction SilentlyContinue
    if (-not $inUse) {
        break
    }
    $port += 1
}

Write-Host "Starting AI Company Enrichment at http://127.0.0.1:$port"
& $python -m uvicorn app.main:app --host 127.0.0.1 --port $port
