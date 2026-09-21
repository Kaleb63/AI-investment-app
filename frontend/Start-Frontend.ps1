param([switch]$Build)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$runtimeRoot = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node'
$nodePath = if ($nodeCommand) { $nodeCommand.Source } else { Join-Path $runtimeRoot 'bin\node.exe' }
if (-not (Test-Path -LiteralPath $nodePath)) {
    throw 'Install Node.js 22.12 or newer, reopen PowerShell, and run this script again.'
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'node_modules\vite\bin\vite.js'))) {
    Write-Host 'Installing the frontend dependencies...'
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npmCommand) {
        & $npmCommand.Source ci
    } else {
        $pnpmPath = Join-Path $runtimeRoot 'node_modules\pnpm\bin\pnpm.cjs'
        if (-not (Test-Path -LiteralPath $pnpmPath)) { throw 'npm was not found. Install Node.js with npm first.' }
        & $nodePath $pnpmPath dlx npm@11 ci
    }
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the error above.' }
}
if ($Build) {
    & $nodePath '.\node_modules\typescript\bin\tsc' --noEmit
    if ($LASTEXITCODE -ne 0) { throw 'Type checking failed.' }
    & $nodePath '.\node_modules\vite\bin\vite.js' build
} else {
    Write-Host 'Open http://127.0.0.1:3000. Press Ctrl+C to stop.'
    & $nodePath '.\node_modules\vite\bin\vite.js' --host 127.0.0.1 --port 3000
}
exit $LASTEXITCODE
