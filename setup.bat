@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher was not found. Install Python 3.12 or newer, including the py launcher.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" goto create_venv
goto install_desktop

:create_venv
echo Looking for an installed Python 3.12 or newer...
py -3.14 -m venv ".venv" >nul 2>nul
if not errorlevel 1 goto install_desktop
py -3.13 -m venv ".venv" >nul 2>nul
if not errorlevel 1 goto install_desktop
py -3.12 -m venv ".venv" >nul 2>nul
if not errorlevel 1 goto install_desktop
echo Could not create the environment with Python 3.12, 3.13, or 3.14.
echo Install Python 3.12 or newer and make sure the Python Launcher can find it.
goto failed

:install_desktop
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -e ".[desktop]"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import PySide6, projectg" >nul 2>nul
if errorlevel 1 goto failed

echo.
echo Desktop setup complete. Use run.bat or start-planner.bat.
pause
exit /b 0

:failed
echo.
echo Setup failed. Review the error above.
pause
exit /b 1
