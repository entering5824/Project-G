$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = if ($env:GENSHIN_PYTHON) { $env:GENSHIN_PYTHON } else { Join-Path $projectRoot '.venv\Scripts\python.exe' }
$env:PYTHONPATH = Join-Path $projectRoot 'src'

if (-not (Test-Path -LiteralPath $python)) {
  throw 'Desktop Python environment is missing. Run setup.bat once before launching Planner.'
}

Push-Location $projectRoot
try {
  try {
    & $python -c 'import PySide6, projectg' 2>$null
  }
  catch {
    throw "Could not start the desktop Python interpreter at '$python'. $($_.Exception.Message)"
  }
  if ($LASTEXITCODE -ne 0) {
    throw 'Desktop dependencies are missing or the environment is broken. Run setup.bat to repair the desktop environment.'
  }

  $env:GENSHIN_ENVIRONMENT = 'desktop'
  try {
    & $python -m projectg.main
  }
  catch {
    throw "Could not launch Genshin Planner with '$python'. $($_.Exception.Message)"
  }
  if ($LASTEXITCODE -ne 0) {
    throw "Genshin Planner exited with code $LASTEXITCODE. Check the local logs folder for details."
  }
}
finally {
  Pop-Location
}
