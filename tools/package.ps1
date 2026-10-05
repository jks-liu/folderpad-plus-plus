param([string]$Version)
# Package the tested x64 DLL and matching complete source. Does not rebuild.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/version-lib.ps1"
$current = Get-FolderpadVersion $root
if ($Version -and $Version -ne $current) { throw "Package version must match src/version.h ($current)." }
$Version = $current
$dllVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo("$root/build/x86_64/folderpad++.dll").ProductVersion
if ($dllVersion -ne $Version) { throw "DLL version ($dllVersion) differs from source ($Version); run tools/build.ps1 first." }
$stage = "$root/build/package-$Version-$([guid]::NewGuid().ToString('N'))"
$binary = "$stage/binary"
$source = "$stage/source"
New-Item -ItemType Directory -Force "$binary/plugins/folderpad++", $source, "$root/dist" | Out-Null
Copy-Item -LiteralPath "$root/build/x86_64/folderpad++.dll" -Destination "$binary/plugins/folderpad++/folderpad++.dll" -Force
Copy-Item "$root/README.md", "$root/LICENSE" $binary -Force
foreach ($name in @('src','vendor','tests','tools','docs','README.md','LICENSE','.gitignore')) {
    Copy-Item -LiteralPath "$root/$name" -Destination $source -Recurse -Force
}
Compress-Archive "$binary/*" "$root/dist/folderpad++-$Version-x64.zip" -Force
Compress-Archive "$source/*" "$root/dist/folderpad++-$Version-source.zip" -Force
Get-FileHash "$root/dist/folderpad++-$Version-*.zip" -Algorithm SHA256 | Format-Table Hash,Path
