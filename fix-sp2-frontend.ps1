param(
    [switch]$SkipDev,
    [switch]$StopNodeProcesses
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$frontendPath = 'C:\Users\24364\sp2_project\sp2-frontend'
$expectedRoot = 'C:\Users\24364\sp2_project'

function Resolve-ExistingDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $resolved.Path -PathType Container)) {
        throw "Path is not a directory: $Path"
    }

    return [System.IO.Path]::GetFullPath($resolved.Path).TrimEnd('\')
}

function Assert-ChildPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Child,
        [Parameter(Mandatory = $true)]
        [string]$Parent
    )

    $childFull = [System.IO.Path]::GetFullPath($Child).TrimEnd('\')
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\')

    if ($childFull -ne $parentFull -and -not $childFull.StartsWith($parentFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside expected root. Path: $childFull"
    }
}

function Remove-IfExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [switch]$Recurse
    )

    if (Test-Path -LiteralPath $Path) {
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            try {
                Write-Host "Removing $Path"
                if ($Recurse) {
                    Remove-Item -LiteralPath $Path -Recurse -Force
                }
                else {
                    Remove-Item -LiteralPath $Path -Force
                }
                return
            }
            catch {
                if ($attempt -eq 3) {
                    throw "Could not remove '$Path'. Close any running Vite/Node terminals and rerun, or rerun with -StopNodeProcesses if it is safe to stop all node.exe processes. Original error: $($_.Exception.Message)"
                }

                Write-Warning "Remove failed, retrying in 2 seconds. Attempt $attempt of 3. $($_.Exception.Message)"
                Start-Sleep -Seconds 2
            }
        }
    }
}

function Stop-NodeProcesses {
    $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
    if (-not $nodeProcesses) {
        return
    }

    $failedProcessIds = @()
    foreach ($process in $nodeProcesses) {
        try {
            Stop-Process -Id $process.Id -Force -ErrorAction Stop
        }
        catch {
            $failedProcessIds += $process.Id
        }
    }

    if ($failedProcessIds.Count -gt 0) {
        $ids = $failedProcessIds -join ', '
        throw "Could not stop node.exe process id(s): $ids. Close those Node/Vite terminals manually, or run this script from an elevated PowerShell."
    }

    Start-Sleep -Seconds 2
}

$root = Resolve-ExistingDirectory -Path $expectedRoot
$frontend = Resolve-ExistingDirectory -Path $frontendPath
Assert-ChildPath -Child $frontend -Parent $root

$packageJson = Join-Path $frontend 'package.json'
$nodeModules = Join-Path $frontend 'node_modules'
$packageLock = Join-Path $frontend 'package-lock.json'

Assert-ChildPath -Child $packageJson -Parent $frontend
Assert-ChildPath -Child $nodeModules -Parent $frontend
Assert-ChildPath -Child $packageLock -Parent $frontend

if ($StopNodeProcesses) {
    Write-Warning "Stopping all node.exe processes because -StopNodeProcesses was supplied."
    Stop-NodeProcesses
}

$cleanPackageJson = @'
{
  "name": "sp2-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.7",
    "vite": "^8.0.16",
    "vue": "^3.5.35",
    "vue-router": "^4.6.4"
  }
}
'@

Write-Host "Writing package.json as UTF-8 without BOM"
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($packageJson, $cleanPackageJson + [Environment]::NewLine, $utf8NoBom)

Remove-IfExists -Path $nodeModules -Recurse
Remove-IfExists -Path $packageLock

Push-Location -LiteralPath $frontend
try {
    Write-Host "Cleaning npm cache"
    & npm cache clean --force
    if ($LASTEXITCODE -ne 0) {
        throw "npm cache clean failed with exit code $LASTEXITCODE"
    }

    Write-Host "Installing dependencies"
    & npm install
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed with exit code $LASTEXITCODE"
    }

    if ($SkipDev) {
        Write-Host "Skipping Vite start because -SkipDev was supplied"
    }
    else {
        Write-Host "Starting Vite"
        & npm run dev
        if ($LASTEXITCODE -ne 0) {
            throw "npm run dev failed with exit code $LASTEXITCODE"
        }
    }
}
finally {
    Pop-Location
}
