@echo off
chcp 65001 > nul

echo ======================================
echo  Revenue Assistant Starting...
echo ======================================

:: Check for pnpm
where pnpm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] pnpm is not installed.
    echo Please install pnpm by running the following command in your terminal:
    echo   npm install -g pnpm
    echo Then try running start.bat again.
    pause
    goto :EOF
)

echo [1/2] Starting Backend (API Server)...
cd backend

if not exist venv\Scripts\activate.bat goto create_venv
call venv\Scripts\activate.bat
goto start_backend

:create_venv
echo   Virtual environment not found or incomplete.
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
call pnpm install

:start_frontend
start /b pnpm start
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
