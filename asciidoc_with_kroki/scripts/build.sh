#!/usr/bin/env sh
set -eu
set -x  # デバッグ: 実行コマンドを表示

count=0
for f in /documents/*.adoc; do
  [ -f "$f" ] || continue
  count=$((count+1))
  base="${f%.adoc}"

  # HTML（Kroki + MathJax は docinfo.html で）
  asciidoctor -r asciidoctor-kroki \
    -a stem=latexmath \
    -a docinfo=shared \
    -a docinfodir=/documents \
    -a scripts=cjk \
    -a kroki-server-url=http://kroki:8000 \
    -a kroki-fetch \
    -a kroki-http-method=post \
    -a allow-uri-read \
    -o "${base}.html" "$f"

  # PDF（数式は asciidoctor-mathematical、図は Kroki）
  asciidoctor-pdf -r asciidoctor-kroki -r asciidoctor-mathematical \
    --theme "asciidoctor-pdf-theme.yml" \
    -a stem=latexmath -a mathematical-format=svg \
    -a pdf-fontsdir=/documents/fonts \
    -a scripts=cjk \
    -a kroki-server-url=http://kroki:8000 \
    -a kroki-fetch \
    -a kroki-http-method=post \
    -a allow-uri-read \
    -o "${base}.pdf" "$f"
done

# 一件も処理していない場合は明示的にエラーにする
[ "$count" -gt 0 ] || { echo "No .adoc files under /documents"; exit 1; }

