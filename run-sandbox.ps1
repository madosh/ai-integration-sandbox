# Boot the full AI Integration Sandbox (mock APIs, service, dashboard).
#
# Windows (recommended — works when script execution is restricted):
#   run-sandbox.cmd
#   run-sandbox.cmd -NoUi
#
# Or:
#   python tasks.py sandbox
#
# PowerShell directly (requires execution policy to allow scripts):
#   .\run-sandbox.ps1
#   .\run-sandbox.ps1 -NoUi

param(
    [switch]$NoUi
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

function Get-PythonExe {
    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    return "python"
}

function Ensure-Setup {
    if (-not (Test-Path (Join-Path $Root ".venv"))) {
        Write-Host "No .venv found - running setup..." -ForegroundColor Yellow
        $py = Get-PythonExe
        & $py tasks.py setup
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

function Start-SandboxWindow {
    param(
        [string]$Title,
        [string]$Target
    )
    $py = Get-PythonExe
    # Build cmd chain with -f so PowerShell 5.1 does not parse && as an operator.
    $inner = ('title {0} && cd /d "{1}" && "{2}" tasks.py {3}' -f $Title, $Root, $py, $Target)
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $inner -WorkingDirectory $Root | Out-Null
}

Ensure-Setup

Write-Host ""
Write-Host "Starting AI Integration Sandbox..." -ForegroundColor Cyan
Write-Host ""

Start-SandboxWindow -Title "aih-mock-apis-9000" -Target "mock-apis"
Start-Sleep -Seconds 2
Start-SandboxWindow -Title "aih-service-8000" -Target "run"

if (-not $NoUi) {
    Start-SandboxWindow -Title "aih-dashboard-5173" -Target "ui"
}

Write-Host "  Mock APIs:  http://127.0.0.1:9000"
Write-Host "  Service:    http://127.0.0.1:8000/docs"
if (-not $NoUi) {
    Write-Host "  Dashboard:  http://127.0.0.1:5173"
}
Write-Host ""
Write-Host "Three service windows should now be open. Close them to stop the sandbox." -ForegroundColor DarkGray
Write-Host "This launcher window can be closed." -ForegroundColor DarkGray
