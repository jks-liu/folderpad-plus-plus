@echo off
setlocal
rem Double-click to install. Arguments are forwarded to the PowerShell script.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
set "folderpadExit=%errorlevel%"
if "%~1"=="" pause
exit /b %folderpadExit%
