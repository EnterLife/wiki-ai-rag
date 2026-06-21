@echo off
setlocal

set "ROOT=%~dp0.."
set "WEB_DIR=%ROOT%\apps\web"
set "WEB_HOST=%WEB_HOST%"
set "WEB_PORT=%WEB_PORT%"

if "%WEB_HOST%"=="" set "WEB_HOST=127.0.0.1"
if "%WEB_PORT%"=="" set "WEB_PORT=5173"
if "%VITE_API_BASE_URL%"=="" set "VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1"

echo [Wiki AI RAG] Starting web UI on http://%WEB_HOST%:%WEB_PORT%
echo [Wiki AI RAG] API base URL: %VITE_API_BASE_URL%
cd /d "%WEB_DIR%" || exit /b 1
call npm run dev -- --host "%WEB_HOST%" --port "%WEB_PORT%"
