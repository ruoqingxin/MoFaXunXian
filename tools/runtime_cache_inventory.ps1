param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

$cacheRoot = Join-Path $env:APPDATA "Tencent\xwechat\XPlugin\Plugins\RadiumWMPF"
$lines = New-Object System.Collections.Generic.List[string]

$lines.Add("USER=$env:USERNAME")
$lines.Add("CACHE_ROOT=$cacheRoot")
$lines.Add("GENERATED_AT=$(Get-Date -Format o)")
$lines.Add("")

if (-not (Test-Path -LiteralPath $cacheRoot)) {
    $lines.Add("CACHE_ROOT_NOT_FOUND")
} else {
    $lines.Add("ROOT_ITEMS")
    Get-ChildItem -LiteralPath $cacheRoot -Force -ErrorAction Stop |
        ForEach-Object {
            $lines.Add(("{0}`t{1}`t{2}`t{3}" -f $_.Mode, $_.Length, $_.LastWriteTime.ToString("o"), $_.FullName))
        }

    $lines.Add("")
    $lines.Add("RECENT_FILES")
    Get-ChildItem -LiteralPath $cacheRoot -Force -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-2) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5000 |
        ForEach-Object {
            $lines.Add(("{0}`t{1}`t{2}" -f $_.Length, $_.LastWriteTime.ToString("o"), $_.FullName))
        }

    $lines.Add("")
    $lines.Add("DIRECTORIES")
    Get-ChildItem -LiteralPath $cacheRoot -Force -Recurse -Directory -ErrorAction SilentlyContinue |
        Sort-Object FullName |
        ForEach-Object {
            $lines.Add(("{0}`t{1}" -f $_.LastWriteTime.ToString("o"), $_.FullName))
        }
}

$parent = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

$lines | Set-Content -LiteralPath $OutputPath -Encoding UTF8
