param(
    [Parameter(Position=0)][string]$Version = 'patch',
    [switch]$Build,
    [switch]$NoBuild
)
# Usage: ./tools/version-bump.ps1 [patch|minor|major|X.Y.Z|current] [-Build|-NoBuild]
# Default: patch, no build. No commits, tags, installation or network operations.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/version-lib.ps1"
if ($Build -and $NoBuild) { throw '-Build and -NoBuild cannot be combined.' }
$current = Get-FolderpadVersion $root
if ($Version -eq 'current') {
    if ($Build -or $NoBuild) { throw 'current is read-only; do not combine it with build options.' }
    Write-Output $current
    return
}
$parts = @($current.Split('.') | ForEach-Object { [int]$_ })
switch -CaseSensitive ($Version) {
    'patch' { $parts[2]++ }
    'minor' { $parts[1]++; $parts[2] = 0 }
    'major' { $parts[0]++; $parts[1] = 0; $parts[2] = 0 }
    default {
        if ($Version -cnotmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') {
            throw 'Use patch, minor, major, current, or an exact stable version X.Y.Z.'
        }
        $parts = @($Version.Split('.') | ForEach-Object { [int]::Parse($_) })
    }
}
if (@($parts | Where-Object { $_ -gt 65535 }).Count) { throw 'Version components must be between 0 and 65535 (Windows VERSIONINFO).' }
$next = $parts -join '.'
$path = Join-Path $root 'src/version.h'
$text = [IO.File]::ReadAllText($path)
$names = @('MAJOR','MINOR','PATCH')
for ($i = 0; $i -lt 3; $i++) {
    $text = [regex]::Replace($text, "(?m)^(#define FOLDERPAD_VERSION_$($names[$i]) )[0-9]+", "`${1}$($parts[$i])")
}
if ($next -ne $current) {
    $temp = "$path.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        [IO.File]::WriteAllText($temp, $text, [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temp, $path, $true)
    } finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp } }
}
Write-Output "$current -> $next"
if ($Build) {
    try {
        & "$PSScriptRoot/build.ps1"
        & "$PSScriptRoot/package.ps1"
    } catch { throw "Version is now $next; build/package failed (version retained): $_" }
}
