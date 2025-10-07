@echo off
echo ========================================
echo   Trinity Wealth Scanner - Desktop
echo ========================================
echo Starting Trinity Wealth Scanner locally...
echo.

:: Check if MongoDB is running
echo [1/4] Checking MongoDB...
tasklist /FI "IMAGENAME eq mongod.exe" 2>NUL | find /I /N "mongod.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ✅ MongoDB is running
) else (
    echo ❌ MongoDB not detected. Please start MongoDB first.
    echo    - Install from: https://www.mongodb.com/try/download/community
    echo    - Start service from Windows Services panel
    pause
    exit
)

:: Start Backend
echo.
echo [2/4] Starting Backend Server...
cd backend
start "Trinity Backend" cmd /k "python server.py"
echo ✅ Backend starting on http://localhost:8001

:: Wait a bit for backend to start
timeout /t 3 /nobreak >nul

:: Start Frontend  
echo.
echo [3/4] Starting Frontend...
cd ..\frontend
start "Trinity Frontend" cmd /k "npm start"
echo ✅ Frontend starting on http://localhost:3000

:: Wait for frontend to start
timeout /t 5 /nobreak >nul

:: Open in browser
echo.
echo [4/4] Opening Trinity Wealth Scanner...
start http://localhost:3000

echo.
echo ========================================
echo ✅ Trinity Wealth Scanner is running!
echo ========================================
echo.
echo 📊 Dashboard: http://localhost:3000
echo 🔧 Backend API: http://localhost:8001
echo 💾 Database: mongodb://localhost:27017
echo.
echo Press any key to close this window...
echo (Note: Keep backend and frontend windows open)
pause >nul