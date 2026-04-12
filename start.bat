@echo off
echo Starting Ticket Price Tracker...

:: Start backend
start "Backend" cmd /k "cd /d "%~dp0" && python -m uvicorn backend.main:app --port 8000"

:: Give backend a moment to start
timeout /t 2 /nobreak >nul

:: Start frontend from local node_modules (avoids Google Drive path issue)
start "Frontend" cmd /k "cd /d C:\ticket-frontend-nm && node_modules\.bin\vite --port 3000"

:: Open browser
timeout /t 4 /nobreak >nul
start http://localhost:3000

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Close the two terminal windows to stop the servers.
