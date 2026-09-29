@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto setup
".venv\Scripts\python.exe" -c "import PySide6, projectg" >nul 2>nul
if errorlevel 1 goto setup
goto launch

:setup
echo Desktop Planner has not been set up yet. Running setup.bat first...
call "%~dp0setup.bat"
if errorlevel 1 exit /b 1

:launch
call "%~dp0start-planner.bat"
endlocal
