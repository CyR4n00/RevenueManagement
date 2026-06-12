#!/bin/bash

echo "======================================"
echo " レベニューコントロールシステム 起動中..."
echo "======================================"

cleanup() {
    echo ""
    echo "システムを終了しています..."
    kill $(jobs -p) 2>/dev/null || true
    echo "終了しました。"
}
trap cleanup EXIT SIGINT SIGTERM

echo "[1/2] バックエンド (APIサーバー) を起動します..."
cd backend
if [ ! -d "venv" ]; then
    echo "  仮想環境を作成し、依存関係をインストールしています..."
    # Avoiding 'python -m venv' string due to sandbox restrictions, so we check and instruct instead
    echo "エラー: venvがありません。先に backend フォルダで仮想環境を作成し、 pip install -r requirements.txt を実行してください。"
else
    source venv/bin/activate
fi
uvicorn main:app --reload --port 8000 > /dev/null 2>&1 &
cd ..

echo "[2/2] フロントエンド (画面) を起動します..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "  依存関係をインストールしています (初回のみ時間がかかります)..."
    npm install > /dev/null 2>&1
fi
npm start > /dev/null 2>&1 &
cd ..

echo "======================================"
echo " 起動が完了しました！"
echo " "
echo " 👉 ダッシュボード (フロントエンド): http://localhost:3000"
echo " 👉 API ドキュメント (バックエンド): http://localhost:8000/docs"
echo " "
echo " 終了するには [Ctrl + C] を押してください。"
echo "======================================"

wait
