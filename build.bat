@echo off
REM ──────────────────────────────────────────────────────────────────
REM Build standalone GRACE executable for Windows distribution
REM Requires: pyinstaller
REM ──────────────────────────────────────────────────────────────────

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Building GRACE standalone executable...

pyinstaller --clean --noconfirm GRACE.spec

echo.
echo Done! Standalone executable at:
echo   %SCRIPT_DIR%dist\GRACE.exe
dir "%SCRIPT_DIR%dist\GRACE.exe" 2>nul
