# Registers the daily Windows Task Scheduler job for the automation pipeline.
# This wrapper keeps the expected script name while reusing the existing setup
# script that contains the full Task Scheduler registration logic.
# Usage:
#   .\schedule_pipeline.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupScript = Join-Path $ProjectRoot "setup_windows_task.ps1"

if (-not (Test-Path $SetupScript)) {
    Write-Error "Missing setup script: $SetupScript"
    exit 1
}

& $SetupScript
exit $LASTEXITCODE
