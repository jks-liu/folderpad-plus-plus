param(
    [Parameter(Mandatory)][string]$Tag,
    [string]$ExpectedCommit
)
# Read-only release guard. Usage: ./tools/validate-release-tag.ps1 -Tag releases/v1.2.0
# Requires the tag to have been fetched, PowerShell 7 and Git.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/version-lib.ps1"
if ($Tag -cnotmatch '^releases/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') {
    throw 'Release tag must be releases/vX.Y.Z without leading zeros or suffixes.'
}
$version = Get-FolderpadVersion $root
if ($Tag -cne "releases/v$version") { throw "Tag version differs from src/version.h ($version)." }
$ref = "refs/tags/$Tag"
$kind = & git -C $root cat-file -t $ref
if ($LASTEXITCODE -or $kind -ne 'tag') { throw 'Release requires an existing annotated tag (git tag -a).' }
$commit = & git -C $root rev-parse --verify "$ref^{commit}"
if ($LASTEXITCODE) { throw 'Release tag must point to a commit.' }
$headCommit = & git -C $root rev-parse --verify HEAD
if ($LASTEXITCODE -or $commit -ne $headCommit) { throw 'Checked-out source does not match the release tag.' }
if ($ExpectedCommit) {
    $expected = & git -C $root rev-parse --verify "$ExpectedCommit^{commit}"
    if ($LASTEXITCODE -or $commit -ne $expected) { throw 'Release tag does not match the triggering commit.' }
}
$notes = Join-Path $root "docs/releases/$version.md"
if (-not (Test-Path -LiteralPath $notes -PathType Leaf) -or
    [string]::IsNullOrWhiteSpace([IO.File]::ReadAllText($notes))) {
    throw "Missing or empty release notes: $notes"
}
Write-Host "Validated annotated release tag: $Tag ($commit)"
