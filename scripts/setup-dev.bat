@echo off
setlocal

set "ROOT=%~dp0.."

call "%ROOT%\scripts\setup-api-venv.bat" || exit /b 1
call "%ROOT%\scripts\setup-web.bat" || exit /b 1

echo [Wiki AI RAG] Development environment is ready.
