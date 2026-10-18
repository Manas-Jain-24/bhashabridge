@echo off
title BhashaBridge Frontend Server
cd /d "%~dp0frontend"
set NODE_EXE=C:\Users\HP\AppData\Local\OpenAI\Codex\runtimes\cua_node\a9ba6825a525118c\bin\node.exe
if exist "%NODE_EXE%" (
    echo [*] Starting Vite Frontend on http://localhost:5173 using embedded Node runtime...
    "%NODE_EXE%" "node_modules\vite\bin\vite.js" --host 127.0.0.1 --port 5173
) else (
    echo [*] Starting Vite Frontend on http://localhost:5173...
    npm run dev
)
pause
