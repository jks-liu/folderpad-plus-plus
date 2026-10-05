param([string]$Toolchain, [ValidateSet('x86_64','i686','aarch64')][string]$Arch = 'x86_64')
# Build with llvm-mingw. Example: ./tools/build.ps1 -Toolchain C:/tools/llvm-mingw
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot/version-lib.ps1"
$version = Get-FolderpadVersion $root
if (-not $Toolchain) {
    $found = Get-ChildItem "$root/.cache/toolchain" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $Toolchain = $found.FullName }
}
if (-not $Toolchain) { throw 'Provide -Toolchain pointing to llvm-mingw, or run tools/setup-toolchain.ps1.' }
$cxx = Join-Path $Toolchain "bin/$Arch-w64-mingw32-clang++.exe"
$rc = Join-Path $Toolchain "bin/$Arch-w64-mingw32-windres.exe"
if (-not (Test-Path $cxx)) { throw "Compiler not found: $cxx" }
$out = "$root/build/$Arch"
New-Item -ItemType Directory -Force $out | Out-Null
$common = @('-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-DUNICODE','-D_UNICODE',"-I$root/vendor/npp","-I$root/src",'-static')
& $rc "$root/src/panel.rc" "$out/panel.o"
if ($LASTEXITCODE) { throw 'Resource compilation failed' }
& $cxx @common -shared "$root/src/plugin.cpp" "$out/panel.o" -o "$out/folderpad++.dll" -lcomctl32 -lole32 -lshell32 -luuid '-Wl,--no-insert-timestamp'
if ($LASTEXITCODE) { throw 'Plugin compilation failed' }
& $cxx @common "$root/tests/model_tests.cpp" -o "$out/model_tests.exe"
if ($LASTEXITCODE) { throw 'Test compilation failed' }
if ($Arch -eq 'x86_64') {
    & "$out/model_tests.exe"
    if ($LASTEXITCODE) { throw 'Model tests failed' }
}
Write-Host "Built folderpad++ $version : $out/folderpad++.dll"
