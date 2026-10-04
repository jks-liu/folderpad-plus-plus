param([string]$Proxy)
# Download a pinned portable compiler inside this repository. No PATH or system changes.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$release = '20260922'
$name = "llvm-mingw-$release-ucrt-x86_64"
$cache = "$root/.cache"
New-Item -ItemType Directory -Force "$cache/toolchain" | Out-Null
$params = @{ Uri = "https://github.com/mstorsjo/llvm-mingw/releases/download/$release/$name.zip"; OutFile = "$cache/toolchain.zip" }
if ($Proxy) { $params.Proxy = $Proxy }
Invoke-WebRequest @params
Expand-Archive "$cache/toolchain.zip" "$cache/toolchain" -Force
Write-Host "Toolchain: $cache/toolchain/$name"
