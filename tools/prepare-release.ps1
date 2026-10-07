param(
    [string]$Repository = 'https://github.com/jks-liu/folderpad-plus-plus',
    [string]$Author = 'Jks Liu',
    [string]$CompatibleVersions = '[8.9.8.1,]',
    [switch]$VerifyPublished
)
# Generate local release materials from an existing package; never uploads or commits.
# Usage: ./tools/package.ps1; ./tools/prepare-release.ps1 [-VerifyPublished]
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/version-lib.ps1"
$version = Get-FolderpadVersion $root
$Repository = $Repository.TrimEnd('/')
if ($Repository -notmatch '^https://github\.com/[^/]+/[^/]+$') { throw 'Repository must be a GitHub repository URL.' }
if ($CompatibleVersions -notmatch '^\[(\d+(\.\d+){0,3})?,(\d+(\.\d+){0,3})?\]$' -or $CompatibleVersions -eq '[,]') {
    throw 'Use a compatibility range such as [8.9.8.1,], without spaces.'
}
$dist = Join-Path $root 'dist'
$name = "folderpad++-$version-x64.zip"
$zipPath = Join-Path $dist $name
$dllPath = Join-Path $root 'build/x86_64/folderpad++.dll'
$dllInfo = [Diagnostics.FileVersionInfo]::GetVersionInfo($dllPath)
if ($dllInfo.FileVersion -ne $version -or $dllInfo.ProductVersion -ne $version) { throw 'DLL/source version mismatch.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $dllEntry = $zip.GetEntry('folderpad++.dll')
    if (-not $dllEntry) { throw 'The plugin DLL must be at the ZIP root.' }
    $stream = $dllEntry.Open()
    $memory = [IO.MemoryStream]::new()
    try { $stream.CopyTo($memory); $bytes = $memory.ToArray() } finally { $stream.Dispose(); $memory.Dispose() }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $zipDllHash = [Convert]::ToHexString($sha.ComputeHash($bytes)) } finally { $sha.Dispose() }
    if ($zipDllHash -ne (Get-FileHash -LiteralPath $dllPath -Algorithm SHA256).Hash) { throw 'Packaged DLL differs from the current build.' }
    if ($bytes.Length -lt 64 -or [BitConverter]::ToUInt16($bytes, 0) -ne 0x5A4D) { throw 'Invalid DLL DOS header.' }
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    if ($peOffset -lt 0 -or $peOffset + 6 -gt $bytes.Length -or [BitConverter]::ToUInt32($bytes, $peOffset) -ne 0x4550) { throw 'Invalid DLL PE header.' }
    if ([BitConverter]::ToUInt16($bytes, $peOffset + 4) -ne 0x8664) { throw 'Release requires an x64 DLL.' }
    $entries = @($zip.Entries | ForEach-Object { $_.FullName })
} finally { $zip.Dispose() }
$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
$download = "$Repository/releases/download/v$version/$name"
$entry = [ordered]@{
    'folder-name' = 'folderpad++'
    'display-name' = 'folderpad++'
    'version' = $version
    'npp-compatible-versions' = $CompatibleVersions
    'id' = $hash
    'repository' = $download
    'description' = 'Organize open documents into folder tabs without scanning directories. Supports English and Chinese.'
    'author' = $Author
    'homepage' = $Repository
}
$entry | ConvertTo-Json | Set-Content -LiteralPath "$dist/nppPluginList-entry-x64.json" -Encoding utf8NoBOM
$checksums = foreach ($file in @($zipPath, "$dist/folderpad++-$version-source.zip")) {
    $fileHash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    "$fileHash  $([IO.Path]::GetFileName($file))"
}
$checksums | Set-Content -LiteralPath "$dist/SHA256SUMS.txt" -Encoding utf8NoBOM
$publishedVerified = $false
if ($VerifyPublished) {
    # Compare the actual public bytes with the submission hash after Release upload.
    $temp = Join-Path $root "build/published-$([guid]::NewGuid().ToString('N')).zip"
    try {
        Invoke-WebRequest -Uri $download -OutFile $temp
        if ((Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) { throw 'Published ZIP hash mismatch.' }
        $publishedVerified = $true
    } finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp } }
}
[ordered]@{
    version = $version; architecture = 'x64'; fileVersion = $dllInfo.FileVersion
    productVersion = $dllInfo.ProductVersion; dllSHA256 = $zipDllHash.ToLowerInvariant()
    zipSHA256 = $hash; zipEntries = $entries; downloadURL = $download
    publicDownloadVerified = $publishedVerified
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$dist/release-manifest.json" -Encoding utf8NoBOM
$notes = Join-Path $root "docs/releases/$version.md"
if (-not (Test-Path -LiteralPath $notes)) { throw "Missing release notes: $notes" }
Copy-Item -LiteralPath $notes -Destination "$dist/RELEASE-NOTES.md" -Force
@"
Add folderpad++ $version (x64)

folderpad++ organizes already-open documents into folder tabs in a dockable panel. It does not scan folders. It supports English and Chinese, nested folder ownership, and opening files from a folder tab.

- Architecture: x64 only
- Version: $version
- Compatibility: $CompatibleVersions (conservative minimum based on the tested stable host)
- Download: $download
- ZIP SHA-256: $hash
- DLL is at the ZIP root; FileVersion and ProductVersion match the listed version.

See docs/validation.md in the plugin repository for functional and Plugins Admin test evidence.
Before submitting this PR, upload the frozen ZIP and run tools/prepare-release.ps1 -VerifyPublished.
Only add the entry to src/pl.x64.json; do not modify generated lists or the list version.
"@ | Set-Content -LiteralPath "$dist/NPPPLUGINLIST-PR.md" -Encoding utf8NoBOM
Write-Host "Prepared $version x64: $dist"
Write-Host "SHA-256: $hash"
Write-Host "Public download verified: $publishedVerified"
