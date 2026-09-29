#Requires -Version 5.1
<#
.SYNOPSIS
  DQ Observatory — one-command local demo (backend :8000 + frontend :5173 + demo seed).
.DESCRIPTION
  Starts the FastAPI backend (Python 3.11, SQLite) and the Vite frontend,
  waits for both health checks, seeds the demo dataset and prints the URLs.
  Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts/start-demo.ps1
#>
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = 'C:\Users\USUARIO\AppData\Local\Programs\Python\Python311\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
  $Python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}
if (-not $Python) { throw 'Python 3.11+ not found. Install it first: https://www.python.org/downloads/' }

# 1. Backend env (SQLite default, no Docker needed)
if (-not (Test-Path -LiteralPath "$Root\backend\.env")) {
  Copy-Item -LiteralPath "$Root\.env.example" -Destination "$Root\backend\.env" -Force
  Write-Host '[demo] backend/.env created from .env.example'
}
New-Item -ItemType Directory -Path "$Root\storage" -Force | Out-Null

# 2. Backend (detached)
$backendRunning = $false
try {
  $h = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 3
  if ($h.StatusCode -eq 200) { $backendRunning = $true; Write-Host '[demo] backend already running :8000' }
} catch { }
if (-not $backendRunning) {
  Start-Process -FilePath $Python -ArgumentList '-m uvicorn app.main:app --port 8000 --host 0.0.0.0' `
    -WorkingDirectory "$Root\backend" -WindowStyle Hidden
  Write-Host '[demo] backend starting...'
  for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Seconds 3
    try {
      $h = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 3
      if ($h.StatusCode -eq 200) { $backendRunning = $true; break }
    } catch { }
  }
}
if (-not $backendRunning) { throw 'Backend did not answer on :8000. Check backend logs.' }
Write-Host ('[demo] backend OK: ' + (Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing).Content)

# 3. Seed demo dataset (idempotent — creates a fresh demo dataset each run)
$seed = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/datasets/demo/seed' -Method POST -UseBasicParsing | ConvertFrom-Json
Write-Host ("[demo] dataset seeded: id={0} rows={1}" -f $seed.id, $seed.rows)
$q = Invoke-WebRequest -Uri ("http://localhost:8000/api/v1/datasets/{0}/quality" -f $seed.id) -UseBasicParsing | ConvertFrom-Json
Write-Host ("[demo] quality score: {0}/100" -f $q.score)

# 4. Frontend (detached)
$frontendRunning = $false
try {
  $f = Invoke-WebRequest -Uri 'http://localhost:5173/' -UseBasicParsing -TimeoutSec 3
  if ($f.StatusCode -eq 200) { $frontendRunning = $true; Write-Host '[demo] frontend already running :5173' }
} catch { }
if (-not $frontendRunning) {
  Start-Process -FilePath 'cmd.exe' -ArgumentList '/c npm run dev -- --port 5173 --host 0.0.0.0' `
    -WorkingDirectory "$Root\frontend" -WindowStyle Hidden
  Start-Sleep -Seconds 10
  $f = Invoke-WebRequest -Uri 'http://localhost:5173/' -UseBasicParsing
  if ($f.StatusCode -ne 200) { throw 'Frontend did not answer on :5173.' }
}

Write-Host ''
Write-Host '  ============================================'
Write-Host '   DQ Observatory is running:'
Write-Host '   Frontend : http://localhost:5173'
Write-Host '   Backend  : http://localhost:8000  (/docs = OpenAPI)'
Write-Host '   Health   : http://localhost:8000/health'
Write-Host '  --------------------------------------------'
Write-Host '   Public link (ephemeral, 1 command):'
Write-Host '   cloudflared tunnel --url http://localhost:5173'
Write-Host '  ============================================'
