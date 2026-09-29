param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

if ($env:GENSHIN_PYTHON) {
    $python = $env:GENSHIN_PYTHON
}
elseif (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
}
else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw 'Python was not found. Run setup.bat first or set GENSHIN_PYTHON.'
    }
    $python = $pythonCommand.Source
}

Push-Location $root
try {
    & $python -c 'import PyInstaller, PySide6' 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Desktop build dependencies are missing. Install with: .venv\Scripts\python.exe -m pip install -e ".[desktop-build]"'
    }

    if ($Clean) {
        Remove-Item -LiteralPath (Join-Path $root 'build\desktop') -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $root 'dist\GenshinPlanner') -Recurse -Force -ErrorAction SilentlyContinue
    }

    & $python -m PyInstaller --noconfirm --clean --windowed --onedir --name GenshinPlanner `
        --paths (Join-Path $root 'src') `
        --add-data "$root\assets\genshin-impact;assets\genshin-impact" `
        --add-data "$root\data\static\genshin-impact;data\static\genshin-impact" `
        --add-data "$root\data\static\builds\build_profiles.json;data\static\builds" `
        --add-data "$root\alembic.ini;." `
        --add-data "$root\migrations;migrations" `
        --collect-all tzdata `
        --distpath (Join-Path $root 'dist') `
        --workpath (Join-Path $root 'build\desktop') --specpath (Join-Path $root 'build\desktop') `
        (Join-Path $root 'src\projectg\main.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $release = Join-Path $root 'dist'
    $app = Join-Path $release 'GenshinPlanner'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install-desktop.ps1') -Destination (Join-Path $release 'Install-GenshinPlanner.ps1') -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install-desktop.bat') -Destination (Join-Path $release 'Install-GenshinPlanner.bat') -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'uninstall-desktop.ps1') -Destination (Join-Path $app 'Uninstall-GenshinPlanner.ps1') -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'uninstall-desktop.bat') -Destination (Join-Path $app 'Uninstall-GenshinPlanner.bat') -Force
    $portable = Join-Path $release 'GenshinPlanner-portable.zip'
    Remove-Item -LiteralPath $portable -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path $app, (Join-Path $release 'Install-GenshinPlanner.ps1'), (Join-Path $release 'Install-GenshinPlanner.bat') -DestinationPath $portable -CompressionLevel Optimal
    Write-Host "Created $(Join-Path $app 'GenshinPlanner.exe')"
    Write-Host "Created $portable (extract, then run Install-GenshinPlanner.bat or launch the EXE directly)"
}
finally {
    Pop-Location
}
