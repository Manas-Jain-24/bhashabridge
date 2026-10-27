@echo off
setlocal enabledelayedexpansion
title BhashaBridge Backend Server

echo ===================================================
echo   BhashaBridge FastAPI Backend Launcher
echo ===================================================
echo.

cd /d "%~dp0backend"

set PYTHON_EXE=

REM 1. Check for dedicated project virtual environment
if exist ".\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\.venv\Scripts\python.exe"
    echo [*] Using virtual environment at backend\.venv
) else if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=..\.venv\Scripts\python.exe"
    echo [*] Using virtual environment at .venv
) else (
    REM 2. Check for system python
    where python.exe >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python.exe"
        echo [!] Warning: backend\.venv not found. Using system Python.
    ) else (
        where py.exe >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=py.exe -3"
            echo [!] Warning: backend\.venv not found. Using py launcher.
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found on your system or in backend\.venv!
    echo.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Then set up the virtual environment:
    echo   cd backend
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 3. Check if uvicorn is installed
%PYTHON_EXE% -c "import uvicorn, fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Required dependencies are missing from %PYTHON_EXE%!
    echo.
    echo Please run the following command to install dependencies:
    echo   %PYTHON_EXE% -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [*] Starting BhashaBridge FastAPI server on http://127.0.0.1:8000 ...
echo [*] Interactive API Docs available at: http://127.0.0.1:8000/docs
echo [*] Health Check available at: http://127.0.0.1:8000/api/health
echo.

%PYTHON_EXE% -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Backend server stopped unexpectedly with error code %errorlevel%.
)

pause
