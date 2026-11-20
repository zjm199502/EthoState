$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $python -m PyInstaller --noconfirm --windowed --onedir --name EthoState --icon ethostate.ico --add-data 'ethostate.ico;.' app.py
if ($LASTEXITCODE) { throw 'PyInstaller failed' }
& $python collect_licenses.py
if ($LASTEXITCODE) { throw 'License collection failed' }
$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($compiler) { $iscc = $compiler.Source } else { $iscc = "$env:LOCALAPPDATA/Programs/Inno Setup 6/ISCC.exe" }
& $iscc installer.iss
if ($LASTEXITCODE) { throw 'Inno Setup failed' }

