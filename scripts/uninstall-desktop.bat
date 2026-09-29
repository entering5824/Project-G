@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Uninstall-GenshinPlanner.ps1"
if errorlevel 1 (
  echo.
  echo Uninstall failed. Review the error above.
  pause
  exit /b 1
)
