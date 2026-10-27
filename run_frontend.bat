@echo off
setlocal enabledelayedexpansion
title BhashaBridge Frontend Server

echo ===================================================
echo   BhashaBridge React + Vite Frontend Launcher
echo ===================================================
echo.

cd /d "%~dp0frontend"

REM 1. Check if node_modules exists
if not exist "node_modules" (
    echo [!] Warning: frontend/node_modules directory was not found.
    echo [*] Attempting to install frontend dependencies...
    where npm.cmd >nul 2>&1
    if !errorlevel! equ 0 (
        call npm.cmd install
    ) else (
        where npm >nul 2>&1
        if !errorlevel! equ 0 (
            call npm install
        ) else (
            echo [ERROR] node_modules is missing and npm was not found on PATH!
            echo Please install Node.js from https://nodejs.org/ and run 'npm install' inside the frontend directory.
            pause
            exit /b 1
        )
    )
)

REM 2. Check if npm is available in PATH
where npm.cmd >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Starting Vite Frontend via npm run dev on http://localhost:5173 ...
    call npm.cmd run dev
    goto :end
)

where npm >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Starting Vite Frontend via npm run dev on http://localhost:5173 ...
    call npm run dev
    goto :end
)

REM 3. Fallback: Check for available Node.js runtimes
set NODE_FALLBACK=
for /f "delims=" %%N in ('where node.exe 2^>nul') do if not defined NODE_FALLBACK set "NODE_FALLBACK=%%N"
if defined NODE_FALLBACK goto :node_ready
if exist "%APPDATA%\Antigravity\bin\agy-node.cmd" (
    set "NODE_FALLBACK=%APPDATA%\Antigravity\bin\agy-node.cmd"
) else if exist "%ProgramFiles%\nodejs\node.exe" (
    set "NODE_FALLBACK=%ProgramFiles%\nodejs\node.exe"
) else if exist "%ProgramFiles(x86)%\nodejs\node.exe" (
    set "NODE_FALLBACK=%ProgramFiles(x86)%\nodejs\node.exe"
) else if exist "%LOCALAPPDATA%\Programs\node\node.exe" (
    set "NODE_FALLBACK=%LOCALAPPDATA%\Programs\node\node.exe"
)

:node_ready
if not "%NODE_FALLBACK%"=="" if exist "node_modules\vite\bin\vite.js" (
    echo [*] Using detected Node runtime: %NODE_FALLBACK%
    echo [*] Starting Vite directly on http://localhost:5173 ...
    call "%NODE_FALLBACK%" "node_modules\vite\bin\vite.js" --host 127.0.0.1 --port 5173
    goto :end
)

echo [ERROR] Node.js and npm were not found on your system PATH!
echo.
echo To run the frontend development server, please:
echo   1. Install Node.js (version 20.19+ or 22.12+) from https://nodejs.org/
echo   2. Re-open terminal and run:
echo        cd frontend
echo        npm install
echo        npm run dev
echo.
pause
exit /b 1

:end
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Frontend server stopped with error code %errorlevel%.
)
pause
