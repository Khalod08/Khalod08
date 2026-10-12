@echo off
rem Double-click this file to open GoatVex (Claude Code in this folder, with GoatVex's Python environment).
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo GoatVex is not set up yet. Open PowerShell in this folder and run:
  echo     powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
  echo.
  pause
  exit /b 1
)
where claude >nul 2>nul
if errorlevel 1 (
  echo Claude Code is not installed yet. Open PowerShell and run:
  echo     irm https://claude.ai/install.ps1 ^| iex
  echo Then close this window and double-click "Start GoatVex" again.
  echo.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
claude
