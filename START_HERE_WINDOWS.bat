@echo off
title VidBrief Setup and Launch

echo.
echo ============================================
echo   VidBrief - YouTube Video Summarizer
echo ============================================
echo.

REM Step 1: Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)
echo [OK] Python found.

REM Step 2: Create virtual environment if it doesn't exist
IF NOT EXIST "venv\" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created.
) ELSE (
    echo [OK] Virtual environment already exists.
)

REM Step 3: Activate venv
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat

REM Step 4: Install dependencies
echo [SETUP] Installing dependencies (this may take a few minutes on first run)...
pip install -r requirements.txt --quiet
echo [OK] All dependencies installed.

REM Step 5: Run the app
echo.
echo ============================================
echo   Starting VidBrief...
echo   Open your browser at: http://127.0.0.1:5001
echo   Press CTRL+C to stop the server
echo ============================================
echo.
python app.py

pause
