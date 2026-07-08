@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ==========================================
echo   テストスクレイピング実行スクリプト
echo ==========================================

:: Check virtual environment and install if needed
if not exist venv\Scripts\activate.bat goto create_venv
call venv\Scripts\activate.bat
:: Make sure requests is installed just in case
uv pip install requests > nul 2>&1
goto run_test

:create_venv
echo [INFO] 仮想環境(venv)が見つかりません。作成し、依存関係をインストールします...
uv venv venv
call venv\Scripts\activate.bat
uv pip install -r requirements.txt

:run_test
echo [INFO] test_scrape.py を実行します...
python test_scrape.py
pause
