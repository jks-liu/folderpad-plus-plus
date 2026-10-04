param([string]$Version = '1.0.0')
# Package the tested x64 DLL and matching complete source. Does not rebuild.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$stage = "$root/build/package-$Version"
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
