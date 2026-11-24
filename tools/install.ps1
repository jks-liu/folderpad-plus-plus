param([string]$NotepadDirectory, [string]$Dll, [switch]$Elevated)

# Works with the Windows PowerShell bundled with Windows and with PowerShell 7.
$ErrorActionPreference = 'Stop'

function Get-PeMachine([string]$Path) {
    $reader = [IO.BinaryReader]::new([IO.File]::OpenRead($Path))
    try {
        $stream = $reader.BaseStream
        if ($stream.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5a4d) { throw "Invalid PE file: $Path" }
        $stream.Position = 0x3c
        $offset = $reader.ReadInt32()
        if ($offset -lt 64 -or $offset -gt $stream.Length - 6) { throw "Invalid PE file: $Path" }
        $stream.Position = $offset
        if ($reader.ReadUInt32() -ne 0x4550) { throw "Invalid PE file: $Path" }
        return $reader.ReadUInt16()
    } finally { $reader.Dispose() }
}

function Find-NotepadExecutable([uint16]$Machine) {
    $directories = @(
        foreach ($view in @('Registry64', 'Registry32')) {
            $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey('LocalMachine', $view)
            try {
                $key = $base.OpenSubKey('SOFTWARE\Notepad++')
                if ($key) {
                    try { $key.GetValue('') } finally { $key.Dispose() }
                }
            } finally { $base.Dispose() }
        }
        foreach ($programFiles in @($env:ProgramW6432, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
            if ($programFiles) { Join-Path $programFiles 'Notepad++' }
        }
    )
    foreach ($directory in ($directories | Select-Object -Unique)) {
        if (!$directory) { continue }
        $candidate = Join-Path $directory 'notepad++.exe'
        if ([IO.File]::Exists($candidate) -and (Get-PeMachine $candidate) -eq $Machine) { return $candidate }
    }
    throw 'No Notepad++ installation matches the DLL architecture. Specify -NotepadDirectory for a custom or portable copy.'
}

function Test-EditorRunning([string]$Exe) {
    foreach ($process in (Get-Process -Name 'notepad++' -ErrorAction SilentlyContinue)) {
        if ($process.Path -eq $Exe) { return $true }
    }
    return $false
}

function Copy-Plugin([string]$Source, [string]$Exe, [string]$Destination) {
    if ([IO.File]::Exists($Destination) -and (Test-EditorRunning $Exe)) { return 2 }
    $directory = Split-Path $Destination -Parent
    $staged = Join-Path $directory ('.folderpad++-' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.Directory]::CreateDirectory($directory) | Out-Null
        [IO.File]::Copy($Source, $staged)
        if ([IO.File]::Exists($Destination)) {
            if (Test-EditorRunning $Exe) { return 2 }
            try {
                [IO.File]::Replace($staged, $Destination, "$Destination.bak")
            } catch [IO.IOException] {
                if (($_.Exception.GetBaseException().HResult -band 0xffff) -in @(32, 33)) { return 2 }
                throw
            }
        } else {
            [IO.File]::Move($staged, $Destination)
        }
    } finally {
        Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue
    }
    return 0
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        return [Security.Principal.WindowsPrincipal]::new($identity).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)
    } finally { $identity.Dispose() }
}

function Quote-PathArgument([string]$Path) {
    # Backslashes immediately before the closing quote need to be doubled.
    return '"' + ($Path -replace '(\\+)$', '$1$1') + '"'
}

try {
    if ($Elevated -and !(Test-Administrator)) { throw 'Administrator access is required for this installation.' }
    if (!$Dll) {
        $Dll = Join-Path $PSScriptRoot 'folderpad++.dll'
        if (![IO.File]::Exists($Dll)) { $Dll = Join-Path (Split-Path $PSScriptRoot -Parent) 'build/x86_64/folderpad++.dll' }
    }
    $source = (Get-Item -LiteralPath $Dll).FullName
    $machine = Get-PeMachine $source
    $exe = if ($NotepadDirectory) { Join-Path $NotepadDirectory 'notepad++.exe' } else { Find-NotepadExecutable $machine }
    $exe = (Get-Item -LiteralPath $exe).FullName
    if ((Get-PeMachine $exe) -ne $machine) { throw "DLL architecture does not match $exe." }
    $directory = Split-Path $exe -Parent
    $destination = Join-Path $directory 'plugins/folderpad++/folderpad++.dll'

    try {
        $status = Copy-Plugin $source $exe $destination
    } catch [UnauthorizedAccessException] {
        if ($Elevated -or (Test-Administrator)) { throw }
        Write-Host "Requesting administrator access to install into $directory"
        $engine = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
        $arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File {0} -NotepadDirectory {1} -Dll {2} -Elevated' -f (
            Quote-PathArgument $PSCommandPath), (Quote-PathArgument $directory), (Quote-PathArgument $source)
        try {
            $worker = Start-Process -FilePath $engine -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -Wait -PassThru
        } catch {
            $failure = $_.Exception.GetBaseException()
            if ($failure -is [ComponentModel.Win32Exception] -and $failure.NativeErrorCode -eq 1223) {
                throw 'The administrator approval was canceled. Run the installer again to install the plugin.'
            }
            throw
        }
        $status = $worker.ExitCode
    }

    switch ($status) {
        0 { if (!$Elevated) { Write-Host "Installed $destination. Restart Notepad++ to load the plugin." } }
        2 {
            if (!$Elevated) {
                Write-Warning "Save your work and close Notepad++ at $exe, then run the installer again."
            }
        }
        default { throw "Installation with administrator access failed for $destination (exit code $status)." }
    }
    exit $status
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
