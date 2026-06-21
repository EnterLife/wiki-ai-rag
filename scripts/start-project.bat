@echo off
setlocal

set "ROOT=%~dp0.."
set "API_PORT=%API_PORT%"
set "WEB_PORT=%WEB_PORT%"

if "%API_PORT%"=="" set "API_PORT=8000"
if "%WEB_PORT%"=="" set "WEB_PORT=5173"

call "%ROOT%\scripts\start-infra.bat" || exit /b 1

echo [Wiki AI RAG] Opening API and Web in separate windows...
start "Wiki AI RAG API" cmd /k "cd /d ""%ROOT%"" && set API_PORT=%API_PORT% && call scripts\start-api.bat"
start "Wiki AI RAG Web" cmd /k "cd /d ""%ROOT%"" && set WEB_PORT=%WEB_PORT% && set VITE_API_BASE_URL=http://127.0.0.1:%API_PORT%/api/v1 && call scripts\start-web.bat"

echo [Wiki AI RAG] API: http://127.0.0.1:%API_PORT%/api/v1/health
echo [Wiki AI RAG] Web: http://127.0.0.1:%WEB_PORT%
