@echo off
chcp 65001 >nul

echo ======================================
echo  レベニューコントロールシステム 起動中...
echo ======================================

echo [1/2] バックエンド (APIサーバー) を起動します...
cd backend

if not exist venv\ goto no_venv
call venv\Scripts\activate.bat
goto start_backend

:no_venv
echo   仮想環境がありません。先に pip install -r requirements.txt 等を行ってください。

:start_backend
start /b uvicorn main:app --reload --port 8000
cd ..

echo [2/2] フロントエンド (画面) を起動します...
cd frontend

if not exist node_modules\ goto install_npm
goto start_frontend

:install_npm
echo   依存関係をインストールしています (初回のみ時間がかかります)...
call npm install

:start_frontend
start /b npm start
cd ..

echo ======================================
echo  起動が完了しました！
echo
echo  👉 ダッシュボード (フロントエンド): http://localhost:3000
echo  👉 API ドキュメント (バックエンド): http://localhost:8000/docs
echo
echo  ※ コマンドプロンプトを閉じるとサーバーが終了します。
echo ======================================
pause
