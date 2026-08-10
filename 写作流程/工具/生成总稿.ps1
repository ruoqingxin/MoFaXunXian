param()

$workspaceRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$catalog = Get-ChildItem -LiteralPath $workspaceRoot -Recurse -File -Filter '16_*.md' |
    Select-Object -First 1

if (-not $catalog) {
    throw 'Cannot locate the canonical settings directory.'
}

$settingsDir = $catalog.DirectoryName
$workflowDir = Split-Path $PSScriptRoot -Parent
$masterDirName = -join ([char[]](0x603b, 0x7a3f))
$settingsMasterName = -join ([char[]](0x8bbe, 0x5b9a, 0x603b, 0x7a3f))
$workflowMasterName = -join ([char[]](0x5199, 0x4f5c, 0x6d41, 0x7a0b, 0x603b, 0x7a3f))
$masterDir = Join-Path $workspaceRoot $masterDirName

if (-not (Test-Path -LiteralPath $masterDir)) {
    New-Item -ItemType Directory -Path $masterDir | Out-Null
}

function Join-SourceFiles {
    param(
        [System.IO.FileInfo[]]$Files,
        [string]$OutputPath
    )

    $parts = New-Object System.Collections.Generic.List[string]
    $parts.Add('<!-- GENERATED FILE: edit source files, then run the generator again. -->')

    foreach ($file in $Files) {
        $parts.Add("`n---`n`n<!-- SOURCE: $($file.Name) -->`n")
        $parts.Add((Get-Content -Raw -LiteralPath $file.FullName -Encoding UTF8).Trim())
    }

    $text = ($parts -join "`n") + "`n"
    $utf8Bom = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::WriteAllText($OutputPath, $text, $utf8Bom)
}

$settingsFiles = Get-ChildItem -LiteralPath $settingsDir -File |
    Where-Object { $_.Name -match '^(0[0-9]|1[0-6])_' -and $_.Extension -eq '.md' } |
    Sort-Object Name

$workflowFiles = Get-ChildItem -LiteralPath $workflowDir -File |
    Where-Object { $_.Name -match '^(00_|[1-5]\.)' } |
    Sort-Object Name

$settingsOutput = Join-Path $masterDir "$settingsMasterName.md"
$workflowOutput = Join-Path $masterDir "$workflowMasterName.md"

Join-SourceFiles -Files $settingsFiles -OutputPath $settingsOutput
Join-SourceFiles -Files $workflowFiles -OutputPath $workflowOutput

Write-Host "Settings master: $settingsOutput ($($settingsFiles.Count) sources)" -ForegroundColor Green
Write-Host "Workflow master: $workflowOutput ($($workflowFiles.Count) sources)" -ForegroundColor Green
