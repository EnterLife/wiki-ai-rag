@echo off
setlocal

set "ROOT=%~dp0.."

echo [Wiki AI RAG] Running backend checks...
cd /d "%ROOT%\apps\api" || exit /b 1
".venv\Scripts\python.exe" -m compileall src tests || exit /b 1
".venv\Scripts\python.exe" -m pytest -q || exit /b 1
".venv\Scripts\python.exe" -m ruff check src tests || exit /b 1

echo [Wiki AI RAG] Running frontend checks...
cd /d "%ROOT%\apps\web" || exit /b 1
call npm run lint || exit /b 1
call npm run build || exit /b 1
call npm audit || exit /b 1

echo [Wiki AI RAG] All checks passed.
