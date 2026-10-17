param()

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$localDirectory = Join-Path $projectRoot '.local'
$statePath = Join-Path $localDirectory 'app-processes.json'
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$frontendLauncher = Join-Path $projectRoot 'frontend\Start-Frontend.ps1'
$powershellPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$backendUrl = 'http://127.0.0.1:8000'
$frontendUrl = 'http://127.0.0.1:3000'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The Python environment is missing. Create .venv using Python 3.12 or newer, then run .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt. See the README for setup.'
}
if (-not (Test-Path -LiteralPath $frontendLauncher)) {
    throw "The frontend launcher was not found: $frontendLauncher"
}
New-Item -ItemType Directory -Path $localDirectory -Force | Out-Null

# Keep previous launch records so running Start-App twice does not lose ownership.
$script:ownedProcesses = @()
if (Test-Path -LiteralPath $statePath) {
    try {
        $savedState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($savedState.projectRoot -ne $projectRoot) {
            throw 'The launch record belongs to another project directory.'
        }
        $script:ownedProcesses = @($savedState.processes)
    } catch {
        throw "Unable to read $statePath. Preserve this file and inspect it before starting another instance."
    }
}

function Save-LaunchRecord {
    param([string]$Name, [System.Diagnostics.Process]$Process)
    $details = Get-CimInstance Win32_Process -Filter "ProcessId = $($Process.Id)"
    if (-not $details) {
        throw "$Name exited during startup. Check its logs in $localDirectory."
    }
    $record = [pscustomobject]@{
        name = $Name
        pid = $Process.Id
        startedUtcTicks = $details.CreationDate.ToUniversalTime().Ticks
        executablePath = $details.ExecutablePath
        commandLine = $details.CommandLine
    }
    $script:ownedProcesses = @($script:ownedProcesses | Where-Object { $_.pid -ne $Process.Id }) + $record
    [pscustomobject]@{
        projectRoot = $projectRoot
        processes = @($script:ownedProcesses)
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

function Test-PortInUse {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Test-Backend {
    try {
        $health = Invoke-RestMethod -Uri "$backendUrl/health" -TimeoutSec 2
        if ($health.status -ne 'healthy') { return $false }
        $schema = Invoke-RestMethod -Uri "$backendUrl/openapi.json" -TimeoutSec 2
        $requiredRoutes = @{
            '/auth/login' = 'post'
            '/auth/register' = 'post'
            '/auth/me' = 'get'
            '/analysis/{ticker}' = 'get'
            '/screen' = 'post'
            '/ai_screen' = 'post'
            '/stock_universe' = 'get'
            '/demo/portfolio_analysis' = 'get'
            '/portfolio_analysis' = 'get'
            '/plaid/connections' = 'get'
            '/watchlist' = 'get'
            '/saved_screens' = 'get'
            '/scan_history' = 'get'
        }
        foreach ($route in $requiredRoutes.Keys) {
            $path = $schema.paths.PSObject.Properties[$route]
            if (-not $path -or -not $path.Value.PSObject.Properties[$requiredRoutes[$route]]) {
                return $false
            }
        }
        return $true
    } catch {
        return $false
    }
}

function Test-Frontend {
    try {
        $response = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200 -and
            $response.Content -match '<title>Aether \| Investment Intelligence</title>' -and
            $response.Content -match '/src/main.tsx'
    } catch {
        return $false
    }
}

function Wait-ForService {
    param([string]$Name, [scriptblock]$Check, [System.Diagnostics.Process]$Process)
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        if (& $Check) { return }
        $Process.Refresh()
        if ($Process.HasExited) {
            throw "$Name exited during startup. Check its logs in $localDirectory."
        }
        Start-Sleep -Milliseconds 400
    }
    throw "$Name did not become ready within 60 seconds. Check its logs in $localDirectory. Run .\Stop-App.ps1 to stop processes started by this launcher."
}

if (Test-PortInUse 8000) {
    if (-not (Test-Backend)) {
        throw 'Port 8000 is occupied by a server that does not expose this app''s current API. Stop that server from its own terminal, then run Start-App.ps1 again.'
    }
    Write-Host "Reusing the compatible backend at $backendUrl"
} else {
    Write-Host 'Starting the backend...'
    $backend = Start-Process -FilePath $pythonPath -ArgumentList @(
        '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000'
    ) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $localDirectory 'backend.stdout.log') `
        -RedirectStandardError (Join-Path $localDirectory 'backend.stderr.log')
    Save-LaunchRecord 'backend' $backend
    Wait-ForService 'Backend' { Test-Backend } $backend
}

if (Test-PortInUse 3000) {
    if (-not (Test-Frontend)) {
        throw 'Port 3000 is occupied by a different application. Stop it from its own terminal, then run Start-App.ps1 again. The backend remains available.'
    }
    Write-Host "Reusing the Aether frontend at $frontendUrl"
} else {
    Write-Host 'Starting the frontend...'
    $frontend = Start-Process -FilePath $powershellPath -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $frontendLauncher + '"')
    ) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $localDirectory 'frontend.stdout.log') `
        -RedirectStandardError (Join-Path $localDirectory 'frontend.stderr.log')
    Save-LaunchRecord 'frontend' $frontend
    Wait-ForService 'Frontend' { Test-Frontend } $frontend
}

Write-Host "Aether is ready: $frontendUrl"
Write-Host "Backend documentation: $backendUrl/docs"
Write-Host "Logs: $localDirectory"
Write-Host 'Run .\Stop-App.ps1 to stop services started by this launcher.'
