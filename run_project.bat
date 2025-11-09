@echo off
title UMKC Healthcare Readmission Project

echo Starting FastAPI backend...
start cmd /k "cd backend && venv\Scripts\activate && uvicorn app:app --host 127.0.0.1 --port 8000 --reload"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo Opening Frontend Dashboard...
start "" "http://127.0.0.1:5000"

echo ----------------------------------------------------
echo  🚀 UMKC Healthcare Readmission App is now running!
echo  Backend: http://127.0.0.1:5000
echo  Frontend: Check your browser (index.html)
echo ----------------------------------------------------
pause
