@echo off
setlocal

set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\apps\api"
set "API_HOST=%API_HOST%"
set "API_PORT=%API_PORT%"

if "%API_HOST%"=="" set "API_HOST=127.0.0.1"
if "%API_PORT%"=="" set "API_PORT=8000"

if not exist "%API_DIR%\.venv\Scripts\python.exe" (
  echo [Wiki AI RAG] Backend venv is missing. Run scripts\setup-api-venv.bat first.
  exit /b 1
)

echo [Wiki AI RAG] Starting API on http://%API_HOST%:%API_PORT%
cd /d "%API_DIR%" || exit /b 1
".venv\Scripts\python.exe" -m uvicorn wiki_ai_rag_api.main:app --host "%API_HOST%" --port "%API_PORT%" --reload
