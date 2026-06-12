@echo off

echo ======================================
echo  Revenue Control System Starting...
echo ======================================

echo [1/2] Starting Backend (API Server)...
cd backend

if not exist venv\ goto create_venv
call venv\Scripts\activate.bat
goto start_backend

:create_venv
echo   Virtual environment not found.
echo   Creating virtual environment and installing dependencies...
echo   (This may take a few minutes for the first time)
python -c "import venv; venv.create('venv', with_pip=True)"
call venv\Scripts\activate.bat
pip install -r requirements.txt

:start_backend
start /b uvicorn main:app --reload --port 8000
cd ..

echo [2/2] Starting Frontend (Dashboard)...
cd frontend

if not exist node_modules\ goto install_npm
goto start_frontend

:install_npm
echo   Installing dependencies (This may take a few minutes)...
call npm install

:start_frontend
start /b npm start
cd ..

echo ======================================
echo  Server Started Successfully!
echo
echo  - Dashboard : http://localhost:3000
echo  - API Docs  : http://localhost:8000/docs
echo
echo  * Closing this window will stop the servers.
echo ======================================
pause
