@echo off
echo ==========================================
echo  Delhi Digital Twin — Startup Script
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause & exit /b 1
)

echo [1/4] Creating Python virtual environment...
cd backend
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] Installing Python packages...
pip install -r requirements.txt --quiet

echo [3/4] Installing Node packages...
cd ..\frontend
npm install --silent

echo [4/4] Starting servers...
echo.
echo  Backend  → http://localhost:8000
echo  Frontend → http://localhost:3000
echo  API Docs → http://localhost:8000/docs
echo.
echo  Press Ctrl+C in each window to stop.
echo.

:: Start backend in new window
cd ..\backend
start "Delhi Twin — Backend" cmd /k "venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"

:: Wait a moment then start frontend
timeout /t 3 /nobreak >nul
cd ..\frontend
start "Delhi Twin — Frontend" cmd /k "npm run dev"

:: Open browser
timeout /t 5 /nobreak >nul
start http://localhost:3000
