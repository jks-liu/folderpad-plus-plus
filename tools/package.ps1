param([string]$Version)
# Package the tested x64 DLL and matching complete source. Does not rebuild.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/version-lib.ps1"
$current = Get-FolderpadVersion $root
if ($Version -and $Version -ne $current) { throw "Package version must match src/version.h ($current)." }
$Version = $current
$dllInfo = [Diagnostics.FileVersionInfo]::GetVersionInfo("$root/build/x86_64/folderpad++.dll")
if ($dllInfo.ProductVersion -ne $Version -or $dllInfo.FileVersion -ne $Version) {
    throw "DLL FileVersion/ProductVersion differs from source ($Version); run tools/build.ps1 first."
}
$stage = "$root/build/package-$Version-$([guid]::NewGuid().ToString('N'))"
$binary = "$stage/binary"
$source = "$stage/source"
# Plugins Admin extracts this ZIP into plugins/folderpad++; the DLL must be at its root.
New-Item -ItemType Directory -Force $binary, $source, "$root/dist" | Out-Null
Copy-Item -LiteralPath "$root/build/x86_64/folderpad++.dll" -Destination "$binary/folderpad++.dll" -Force
Copy-Item "$root/README.md", "$root/LICENSE" $binary -Force
foreach ($name in @('src','vendor','tests','tools','docs','README.md','LICENSE','.gitignore','.gitattributes')) {
    if (Test-Path -LiteralPath "$root/$name" -PathType Container) {
        # Copy source files explicitly: recursive Copy-Item exclusions leave empty cache folders.
        foreach ($file in Get-ChildItem -LiteralPath "$root/$name" -File -Recurse -Force) {
            $relative = [IO.Path]::GetRelativePath($root, $file.FullName)
            if (($relative -split '[\\/]') -contains '__pycache__' -or $file.Extension -eq '.pyc') { continue }
            $destination = Join-Path $source $relative
            New-Item -ItemType Directory -Force (Split-Path $destination -Parent) | Out-Null
            Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
        }
    } else {
        Copy-Item -LiteralPath "$root/$name" -Destination $source -Force
    }
}
Compress-Archive "$binary/*" "$root/dist/folderpad++-$Version-x64.zip" -Force
Compress-Archive "$source/*" "$root/dist/folderpad++-$Version-source.zip" -Force
Get-FileHash "$root/dist/folderpad++-$Version-*.zip" -Algorithm SHA256 | Format-Table Hash,Path
