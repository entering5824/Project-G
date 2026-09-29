@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-planner.ps1"
if errorlevel 1 (
  echo.
  echo Planner stopped with an error. See the message above or %LOCALAPPDATA%\GenshinPlanner\logs.
  echo Press any key to close this window.
  pause >nul
)
endlocal
