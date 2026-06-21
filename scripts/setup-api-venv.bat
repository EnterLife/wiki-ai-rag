@echo off
setlocal

set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\apps\api"

echo [Wiki AI RAG] Setting up backend virtual environment...
cd /d "%API_DIR%" || exit /b 1

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 python -m venv .venv
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -e ".[dev]"

echo [Wiki AI RAG] Backend virtual environment is ready.
