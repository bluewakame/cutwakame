$ErrorActionPreference = 'Stop'
$ff = (Get-Command ffmpeg -ErrorAction Stop).Source
$fp = (Get-Command ffprobe -ErrorAction Stop).Source
python -m PyInstaller --noconfirm --clean --onefile --name CutWakame --paths $PSScriptRoot --distpath $PSScriptRoot --workpath (Join-Path $PSScriptRoot 'build') --specpath $PSScriptRoot --add-binary "$ff;bin" --add-binary "$fp;bin" (Join-Path $PSScriptRoot 'aicut.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }


