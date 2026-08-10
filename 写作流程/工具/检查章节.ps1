param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [int]$MinLength = 2400,
    [int]$MaxLength = 6000,
    [switch]$RequireOverview
)

$resolvedPath = Resolve-Path -LiteralPath $Path -ErrorAction Stop
$content = Get-Content -Raw -LiteralPath $resolvedPath -Encoding UTF8
$body = $content -replace '(?m)^#.*$', '' -replace '\s', ''
$length = $body.Length

$aiTracePattern = '\u3010AI\u6807\u6ce8|\u4ea4\u7a3f\u81ea\u68c0\u62a5\u544a|\u4f5c\u4e3aAI'
$summaryPattern = '\u4ed6\u610f\u8bc6\u5230|\u4ed6\u660e\u767d|\u4ed6\u77e5\u9053'
$oldRealmPattern = '\u884c\u6c14'
$summaryCount = ([regex]::Matches($content, $summaryPattern)).Count
$overviewResult = 'SKIP'
$overviewDetail = 'Draft mode does not require an overview'

if ($RequireOverview) {
    $workspaceRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    $overviewDirName = -join ([char[]](0x7ae0, 0x8282, 0x6982, 0x51b5))
    $overviewSuffix = -join ([char[]](0x6982, 0x51b5))
    $groupName = Split-Path (Split-Path $resolvedPath -Parent) -Leaf
    $chapterBaseName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedPath.Path)
    $overviewFileName = "$($chapterBaseName)_$($overviewSuffix).md"
    $overviewPath = Join-Path (Join-Path (Join-Path $workspaceRoot $overviewDirName) $groupName) $overviewFileName
    $overviewResult = if (Test-Path -LiteralPath $overviewPath) { 'PASS' } else { 'REVIEW' }
    $overviewDetail = $overviewPath
}

$checks = @(
    [pscustomobject]@{ Item = 'Body length'; Result = if ($length -ge $MinLength -and $length -le $MaxLength) { 'PASS' } else { 'REVIEW' }; Detail = "$length chars (target $MinLength-$MaxLength)" }
    [pscustomobject]@{ Item = 'AI traces'; Result = if ($content -match $aiTracePattern) { 'REVIEW' } else { 'PASS' }; Detail = 'No prompts or self-check reports in prose' }
    [pscustomobject]@{ Item = 'ASCII quotes'; Result = if ($content -match '"') { 'REVIEW' } else { 'PASS' }; Detail = 'Use Chinese quotation marks for dialogue' }
    [pscustomobject]@{ Item = 'Ellipsis'; Result = if ($content -match '\.\.\.|\u2026(?!\u2026)') { 'REVIEW' } else { 'PASS' }; Detail = 'Use a paired Chinese ellipsis' }
    [pscustomobject]@{ Item = 'Summary phrases'; Result = if ($summaryCount -gt 2) { 'REVIEW' } else { 'PASS' }; Detail = "$summaryCount matches" }
    [pscustomobject]@{ Item = 'Old realm term'; Result = if ($content -match $oldRealmPattern) { 'REVIEW' } else { 'PASS' }; Detail = 'Use the canonical realm term' }
    [pscustomobject]@{ Item = 'Trailing spaces'; Result = if ($content -match '(?m)[ \t]+$') { 'REVIEW' } else { 'PASS' }; Detail = 'Remove trailing spaces' }
    [pscustomobject]@{ Item = 'Chapter overview'; Result = $overviewResult; Detail = $overviewDetail }
)

$checks | Format-Table -AutoSize

if ($checks.Result -contains 'REVIEW') {
    Write-Host "`nMechanical review items found. Story logic still requires manual review." -ForegroundColor Yellow
    exit 1
}

Write-Host "`nMechanical checks passed. Story logic still requires manual review." -ForegroundColor Green
