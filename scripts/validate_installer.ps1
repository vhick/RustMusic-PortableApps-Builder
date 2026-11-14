param([Parameter(Mandatory=$true)][string]$Installer,[Parameter(Mandatory=$true)][string]$ExpectedSha)
$ErrorActionPreference='Stop'
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) { throw 'No actual generated installer' }
if ($Installer -notmatch '\.paf\.exe$') { throw 'Unexpected installer extension' }
$b=[IO.File]::ReadAllBytes([IO.Path]::GetFullPath($Installer))
if ($b.Length -lt 4096 -or $b[0] -ne 77 -or $b[1] -ne 90) { throw 'Invalid MZ installer' }
$offset=[BitConverter]::ToInt32($b,60)
if ($offset -lt 64 -or $offset+24 -gt $b.Length) { throw 'Bad PE offset' }
if ($b[$offset] -ne 80 -or $b[$offset+1] -ne 69 -or $b[$offset+2] -ne 0 -or $b[$offset+3] -ne 0) { throw 'Installer not PE' }
$arch=[BitConverter]::ToUInt16($b,$offset+4)
if ($arch -notin @(0x14c,0x8664)) { throw "Unexpected installer PE stub architecture: $arch" }
$sha=(Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($sha -ne $ExpectedSha.ToLowerInvariant()) { throw 'Shared builder checksum mismatch' }
$seven=Get-Command 7z.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $seven) { $known=Join-Path $env:ProgramFiles '7-Zip\7z.exe'; if (Test-Path $known) { $seven=$known } }
if (-not $seven) { throw '7-Zip not available: embedded installer verification cannot be completed' }
$output=& $seven l '-slt' $Installer 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect embedded NSIS payload with 7-Zip' }
$joined=($output -join "`n").Replace('/','\')
foreach ($needle in @('RustMusicPortable.exe','App\RustMusic\RustMusic.exe','App\AppInfo\appinfo.ini')) {
  if (-not $joined.Contains($needle)) { throw "Installer payload missing $needle" }
}
Write-Host "Installer PE and embedded files structurally verified SHA256=$sha"
Write-Host 'GUI installation, reininstall, upgrade and rollback remain untested by CI.'
