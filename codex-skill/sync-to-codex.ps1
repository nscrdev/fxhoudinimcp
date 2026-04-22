Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$sourceDir = (Resolve-Path $PSScriptRoot).Path
$repoRoot = Split-Path -Parent $sourceDir
$agentsDir = Join-Path $repoRoot ".agents"
$skillsPath = Join-Path $agentsDir "skills"

if (-not (Test-Path -LiteralPath $agentsDir)) {
    New-Item -ItemType Directory -Path $agentsDir | Out-Null
}

if (Test-Path -LiteralPath $skillsPath) {
    $item = Get-Item -LiteralPath $skillsPath -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Write-Host "Skill link already exists at $skillsPath"
        exit 0
    }

    throw "Cannot create junction because $skillsPath already exists and is not a link."
}

New-Item -ItemType Junction -Path $skillsPath -Target $sourceDir | Out-Null
Write-Host "Created junction:"
Write-Host "  $skillsPath -> $sourceDir"
