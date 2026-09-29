@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Desktop environment is missing. Running setup.bat first...
  call "%~dp0setup.bat"
  if errorlevel 1 exit /b 1
)

echo Installing/updating desktop build dependencies...
".venv\Scripts\python.exe" -m pip install -e ".[desktop-build]"
if errorlevel 1 goto failed

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_desktop.ps1" -Clean
if errorlevel 1 goto failed

echo.
echo Build complete:
echo   dist\GenshinPlanner\GenshinPlanner.exe
echo   dist\GenshinPlanner-portable.zip
exit /b 0

:failed
echo.
echo Desktop build failed. Review the error above.
pause
exit /b 1
