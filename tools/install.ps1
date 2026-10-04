param([string]$NotepadDirectory = 'C:/Program Files/Notepad++', [string]$Dll)
# New installs take effect next launch. Existing DLL updates require closing the editor.
# Never terminates the editor or touches its documents.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not $Dll) { $Dll = "$root/build/x86_64/folderpad++.dll" }
function Get-PeMachine([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $reader = [IO.BinaryReader]::new($stream)
    try { $stream.Position = 0x3c; $offset = $reader.ReadInt32(); $stream.Position = $offset + 4; return $reader.ReadUInt16() }
    finally { $reader.Dispose() }
}
$exe = Join-Path $NotepadDirectory 'notepad++.exe'
if ((Get-PeMachine $exe) -ne (Get-PeMachine $Dll)) { throw 'DLL architecture does not match Notepad++.' }
$target = Join-Path $NotepadDirectory 'plugins/folderpad++'
$dest = Join-Path $target 'folderpad++.dll'
if ((Test-Path $dest) -and (Get-Process notepad++ -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe })) { throw 'Close this Notepad++ instance before updating; documents will not be closed automatically.' }
New-Item -ItemType Directory -Force $target | Out-Null
if (Test-Path $dest) { Copy-Item -LiteralPath $dest -Destination "$dest.bak" -Force }
Copy-Item -LiteralPath $Dll -Destination $dest -Force
Write-Host "Installed $dest. Available on the next Notepad++ launch."
