@echo off
setlocal

set "ROOT=%~dp0.."
set "WEB_DIR=%ROOT%\apps\web"

echo [Wiki AI RAG] Installing frontend dependencies...
cd /d "%WEB_DIR%" || exit /b 1
call npm install || exit /b 1

echo [Wiki AI RAG] Frontend dependencies are ready.
