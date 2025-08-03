#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/output"
DOCS_DIR="$PROJECT_ROOT/docs"
THEME_FILE="$PROJECT_ROOT/asciidoctor-pdf-theme.yml"

echo "=== AsciiDoc to PDF Converter ==="
echo "プロジェクトルート: $PROJECT_ROOT"
echo "出力ディレクトリ: $OUTPUT_DIR"
echo "ドキュメントディレクトリ: $DOCS_DIR"

# 出力ディレクトリの作成
mkdir -p "$OUTPUT_DIR"

# Krokiサーバーの健全性チェック
echo "Krokiサーバーの状態を確認中..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "エラー: Krokiサーバーに接続できません"
    echo "以下のコマンドでKrokiサーバーを起動してください:"
    echo "podman run -d --name kroki -p 8000:8000 yuzutech/kroki"
    exit 1
fi
echo "Krokiサーバーは正常に動作しています"

# AsciiDocファイルの検索と変換
find "$DOCS_DIR" -name "*.adoc" -type f | while read -r adoc_file; do
    echo "変換中: $adoc_file"
    
    # ファイル名からPDFファイル名を生成
    base_name=$(basename "$adoc_file" .adoc)
    pdf_file="$OUTPUT_DIR/${base_name}.pdf"
    
    # AsciiDoctor PDFを実行
    asciidoctor-pdf \
        --require asciidoctor-kroki \
        --attribute kroki-server-url=http://localhost:8000 \
        --attribute pdf-themesdir="$PROJECT_ROOT" \
        --attribute pdf-theme=asciidoctor-pdf-theme \
        --out-file "$pdf_file" \
        "$adoc_file"
    
    if [ $? -eq 0 ]; then
        echo "✓ 変換完了: $pdf_file"
    else
        echo "✗ 変換失敗: $adoc_file"
        exit 1
    fi
done

echo "=== 変換処理が完了しました ==="
echo "生成されたPDFファイル:"
ls -la "$OUTPUT_DIR"/*.pdf 2>/dev/null || echo "PDFファイルが見つかりません"