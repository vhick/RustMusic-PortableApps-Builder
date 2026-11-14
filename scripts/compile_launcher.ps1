param([Parameter(Mandatory=$true)][string]$OutFile)
$ErrorActionPreference='Stop'
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) { throw 'vswhere missing: cannot locate MSVC compiler' }
$install=& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $install) { throw 'MSVC x64 build tools unavailable' }
$module=Join-Path ($install.Trim()) 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll'
if (-not (Test-Path -LiteralPath $module)) { throw "Developer PowerShell not available: $module" }
Import-Module $module
Enter-VsDevShell -VsInstallPath ($install.Trim()) -SkipAutomaticLocation -DevCmdArguments '-arch=amd64'
$src=Join-Path $PSScriptRoot '..\launcher\RustMusicPortable.cpp'
$dest=[IO.Path]::GetFullPath($OutFile)
New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
$flags=@('/nologo','/std:c++17','/EHsc','/O2','/W4','/DUNICODE','/D_UNICODE',"/Fe:$dest",$src,'/link','/SUBSYSTEM:WINDOWS','shell32.lib','user32.lib')
& cl.exe @flags
if ($LASTEXITCODE -ne 0) { throw "MSVC compile failed ($LASTEXITCODE)" }
if (-not (Test-Path -LiteralPath $dest)) { throw 'Missing compiled launcher' }
Write-Host "Compiled launcher: $dest"
