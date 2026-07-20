@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Starting PostgreSQL...
docker compose up -d postgres
if errorlevel 1 (
  echo Docker Compose failed. Is Docker Desktop running?
  exit /b 1
)

echo [2/4] Backend venv + deps...
cd backend
if not exist .venv (
  py -3.12 -m venv .venv
  if errorlevel 1 python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo [3/4] Frontend deps...
cd frontend
call npm install
cd ..

echo [4/4] Done.
echo.
echo Start backend:  cd backend ^&^& .venv\Scripts\activate ^&^& python run.py
echo Start frontend: cd frontend ^&^& npm run dev
echo UI: http://localhost:3000
echo API docs: http://localhost:8020/docs
endlocal
