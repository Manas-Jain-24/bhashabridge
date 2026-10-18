@echo off
title BhashaBridge Backend Server
cd /d "%~dp0backend"
echo [*] Starting BhashaBridge FastAPI Backend on port 8000...
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
pause
