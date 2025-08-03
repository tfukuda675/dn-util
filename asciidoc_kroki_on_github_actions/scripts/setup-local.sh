#!/bin/bash

set -e

echo "=== ローカル環境セットアップ ==="

# Krokiコンテナが既に実行されているかチェック
if podman ps | grep -q kroki; then
    echo "Krokiコンテナは既に実行中です"
else
    # 停止したコンテナがあるかチェック
    if podman ps -a | grep -q kroki; then
        echo "既存のKrokiコンテナを削除中..."
        podman rm -f kroki
    fi
    
    echo "Krokiコンテナを起動中..."
    podman run -d --name kroki -p 8000:8000 yuzutech/kroki
    
    echo "Krokiサーバーの起動を待機中..."
    sleep 30
    
    # 健全性チェック
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null; then
            echo "✓ Krokiサーバーが正常に起動しました"
            break
        else
            echo "Krokiサーバーの起動を待機中... ($i/10)"
            sleep 5
        fi
        
        if [ $i -eq 10 ]; then
            echo "✗ Krokiサーバーの起動に失敗しました"
            exit 1
        fi
    done
fi

echo "=== セットアップ完了 ==="
echo "次のコマンドでPDFを生成できます:"
echo "./scripts/convert-to-pdf.sh"