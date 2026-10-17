param()

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$statePath = Join-Path $projectRoot '.local\app-processes.json'
if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host 'There are no recorded app processes to stop.'
    return
}
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.projectRoot -ne $projectRoot) {
    throw 'The launch record belongs to another project directory. No processes were stopped.'
}

$remaining = @()
foreach ($record in @($state.processes)) {
    $rootProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)"
    if (-not $rootProcess) { continue }
    # PowerShell 7 parses ISO JSON dates as DateTime, while Windows PowerShell
    # leaves strings. Numeric UTC ticks compare consistently in both shells.
    $startedUtcTicks = if ($record.PSObject.Properties['startedUtcTicks']) {
        [long]$record.startedUtcTicks
    } else {
        ([datetime]$record.startedUtc).ToUniversalTime().Ticks
    }
    $sameProcess = $rootProcess.CreationDate.ToUniversalTime().Ticks -eq $startedUtcTicks -and
        $rootProcess.ExecutablePath -eq $record.executablePath -and
        $rootProcess.CommandLine -eq $record.commandLine
    $projectProcess = ($record.name -eq 'backend' -and
        $rootProcess.ExecutablePath -eq (Join-Path $projectRoot '.venv\Scripts\python.exe') -and
        $rootProcess.CommandLine -match 'uvicorn\s+backend\.main:app') -or
        ($record.name -eq 'frontend' -and
        $rootProcess.CommandLine -and
        $rootProcess.CommandLine.Contains((Join-Path $projectRoot 'frontend\Start-Frontend.ps1')))
    if (-not $sameProcess -or -not $projectProcess) {
        Write-Warning "Skipping PID $($record.pid): it no longer matches the process started for this project."
        $remaining += $record
        continue
    }

    # Capture descendants while the verified parent is alive; stop children first.
    $snapshot = @(Get-CimInstance Win32_Process)
    $tree = @($rootProcess)
    for ($index = 0; $index -lt $tree.Count; $index++) {
        $parentProcess = $tree[$index]
        $tree += @($snapshot | Where-Object {
            $_.ParentProcessId -eq $parentProcess.ProcessId -and
            $_.CreationDate -ge $parentProcess.CreationDate
        })
    }
    try {
        for ($index = $tree.Count - 1; $index -ge 0; $index--) {
            $candidate = $tree[$index]
            $current = Get-CimInstance Win32_Process -Filter "ProcessId = $($candidate.ProcessId)"
            if ($current -and $current.CreationDate -eq $candidate.CreationDate -and
                $current.CommandLine -eq $candidate.CommandLine) {
                Stop-Process -Id $current.ProcessId -Force -ErrorAction Stop
            }
        }
        Write-Host "Stopped the $($record.name) started by Start-App.ps1."
    } catch {
        $remaining += $record
        Write-Warning "Could not finish stopping $($record.name): $($_.Exception.Message)"
    }
}
[pscustomobject]@{
    projectRoot = $projectRoot
    processes = @($remaining)
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
