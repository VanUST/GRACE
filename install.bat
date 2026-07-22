@echo off
setlocal enabledelayedexpansion
title GRACE Context Manager — Installer

echo =============================================
echo    GRACE Context Manager — Installer
echo =============================================
echo.

:: ── Step 1: Check / install Python ──────────────────────
echo  • Checking Python...
set PYTHON=

:: Check common install locations
for %%p in (python python3 py) do (
    where %%p >nul 2>&1 && set PYTHON=%%p && goto :found_python
)

:: Check winget
where winget >nul 2>&1
if %errorlevel%==0 (
    echo  - Installing Python 3 via winget...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    :: Refresh PATH
    for /f "tokens=*" %%i in ('where python 2^>nul') do set PYTHON=%%i
    if defined PYTHON goto :found_python
)

echo  X Python 3 not found. Please install from:
echo    https://www.python.org/downloads/
echo  (Check "Add Python to PATH" during install)
pause
exit /b 1

:found_python
echo    √ Found %PYTHON%

:: ── Step 2: Install GRACE ───────────────────────────────────
echo.
echo  • Installing GRACE Context Manager...

set "SCRIPT_DIR=%~dp0"
%PYTHON% -m pip install --user --quiet PyQt6
%PYTHON% -m pip install --user --quiet -e "%SCRIPT_DIR%"

%PYTHON% -c "import grace_app" >nul 2>&1
if %errorlevel%==0 (
    echo    √ GRACE installed successfully
) else (
    echo    X Installation failed
    pause
    exit /b 1
)

:: ── Step 3: Create shortcut ────────────────────────────────
echo.
echo  • Creating desktop shortcut...

set "SHORTCUT=%USERPROFILE%\Desktop\GRACE.lnk"
set "PYTHONPATH=%~dp0grace_app"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%PYTHON%'; $s.Arguments = '-m grace_app.main'; $s.WorkingDirectory = '%USERPROFILE%'; $s.Description = 'GRACE Context Manager'; $s.IconLocation = '%SCRIPT_DIR%grace_app\assets\icon.ico'; $s.Save()"

if exist "%SHORTCUT%" (
    echo    √ Desktop shortcut created
) else (
    echo    - Shortcut creation skipped (desktop not writable)
)

echo.
echo =============================================
echo    Done! Run with:  grace
echo =============================================
echo.
echo  Quick start:
echo    grace          — Launch the app
echo.
echo  Or double-click the GRACE shortcut on your Desktop.
echo.
pause
