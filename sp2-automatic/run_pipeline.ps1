# Runs the full Slay the Spire 2 Run Doctor pipeline from PowerShell.
# Usage:
#   .\run_pipeline.ps1

$ErrorActionPreference = "Stop"

# Resolve the project root from this script's location.
# This avoids hardcoded absolute Windows paths.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $ProjectRoot "logs"
$DataDir = Join-Path $ProjectRoot "data"
$ArchiveDir = Join-Path $ProjectRoot "archive"
$ManualLog = Join-Path $LogsDir "manual_run.log"
$PipelineScript = Join-Path $ProjectRoot "pipeline_runner.py"
$LatestInsights = Join-Path $DataDir "latest_insights.json"

# Create folders before running so logs and output files have a place to go.
New-Item -ItemType Directory -Force -Path $LogsDir, $DataDir, $ArchiveDir | Out-Null

# Start a fresh manual run log for this execution.
"Manual pipeline run started at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $ManualLog

# Activate the local virtual environment when .venv exists.
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    "Activating local virtual environment: $VenvActivate" | Tee-Object -FilePath $ManualLog -Append
    . $VenvActivate
} else {
    "No local .venv found. Using the current Python environment." | Tee-Object -FilePath $ManualLog -Append
}

try {
    "Running pipeline: python pipeline_runner.py" | Tee-Object -FilePath $ManualLog -Append

    Push-Location $ProjectRoot
    try {
        # Capture Python output and append it to logs/manual_run.log.
        & python $PipelineScript 2>&1 | Tee-Object -FilePath $ManualLog -Append
        $PipelineExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($PipelineExitCode -ne 0) {
        "Pipeline failed with exit code $PipelineExitCode." | Tee-Object -FilePath $ManualLog -Append
        exit $PipelineExitCode
    }

    "Pipeline completed successfully." | Tee-Object -FilePath $ManualLog -Append
    "Latest insights JSON: $LatestInsights" | Tee-Object -FilePath $ManualLog -Append
    exit 0
} catch {
    "Pipeline failed: $($_.Exception.Message)" | Tee-Object -FilePath $ManualLog -Append
    exit 1
}
