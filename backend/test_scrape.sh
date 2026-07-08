#!/bin/bash

cd "$(dirname "$0")"

echo "=========================================="
echo "  テストスクレイピング実行スクリプト"
echo "=========================================="

# Check virtual environment and install if needed
if [ ! -d "venv" ]; then
    echo "[INFO] 仮想環境(venv)が見つかりません。作成し、依存関係をインストールします..."
    uv venv venv
    source venv/bin/activate
    uv pip install -r requirements.txt
else
    source venv/bin/activate
    # Make sure requests is installed just in case
    uv pip install requests > /dev/null 2>&1
fi

echo "[INFO] test_scrape.py を実行します..."
python test_scrape.py
