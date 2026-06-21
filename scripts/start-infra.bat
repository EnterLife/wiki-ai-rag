@echo off
setlocal

set "ROOT=%~dp0.."

echo [Wiki AI RAG] Starting PostgreSQL and Qdrant...
cd /d "%ROOT%" || exit /b 1
docker compose -f infra\docker-compose.yml up -d postgres qdrant

echo [Wiki AI RAG] Infrastructure started.
echo Qdrant dashboard: http://localhost:6333/dashboard
