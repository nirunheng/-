@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "MANIFEST=%PROJECT_DIR%assets\manifest.json"
set "PYTHONPATH=%PROJECT_DIR%"

python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found on PATH.
  echo Install Python for Windows, then run: python -m pip install -r "%PROJECT_DIR%requirements-windows.txt"
  pause
  exit /b 1
)

if not exist "%MANIFEST%" (
  echo Missing asset manifest: %MANIFEST%
  echo Run prepare_asset.sh in WSL first.
  pause
  exit /b 1
)

python -m pip show Pillow >nul 2>&1
if errorlevel 1 (
  echo Missing Pillow. Run:
  echo   python -m pip install -r "%PROJECT_DIR%requirements-windows.txt"
  pause
  exit /b 1
)

python -m pip show PyQt5 >nul 2>&1
if errorlevel 1 (
  echo Missing PyQt5. Run:
  echo   python -m pip install -r "%PROJECT_DIR%requirements-windows.txt"
  pause
  exit /b 1
)

python -m windows_app.app --manifest "%MANIFEST%"
