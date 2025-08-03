# AsciiDoc to PDF with Kroki

PodmanとKrokiを使用してAsciiDocからPDFを生成するシステムです。日本語フォントに対応し、MermaidやPlantUMLなどの図表も自動生成できます。

## 特徴

- **日本語対応**: Noto CJKフォントを使用した日本語PDF生成
- **図表自動生成**: Krokiを使用したMermaid、PlantUML、その他の図表フォーマット対応
- **自動化**: GitHub Actionsによる自動PDF生成
- **コンテナベース**: Podmanを使用したポータブルな環境

## 必要な環境

- Podman
- Ruby (AsciiDoctor用)
- curl

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <このリポジトリのURL>
cd asciidoc_kroki_on_github_actions
```

### 2. ローカル環境でのセットアップ

```bash
# AsciiDoctorとプラグインのインストール
gem install asciidoctor asciidoctor-pdf asciidoctor-kroki

# Krokiコンテナの起動
./scripts/setup-local.sh
```

### 3. PDFの生成

```bash
# AsciiDocファイルをPDFに変換
./scripts/convert-to-pdf.sh
```

生成されたPDFは `output/` ディレクトリに保存されます。

## ディレクトリ構造

```
.
├── .github/
│   └── workflows/
│       └── asciidoc-to-pdf.yml    # GitHub Actionsワークフロー
├── docs/
│   └── sample.adoc                # サンプルAsciiDocファイル
├── scripts/
│   ├── convert-to-pdf.sh          # PDF変換スクリプト
│   └── setup-local.sh             # ローカル環境セットアップ
├── output/                        # 生成されたPDFの出力先
├── asciidoctor-pdf-theme.yml      # PDFテーマ設定
└── README.md
```

## 使用方法

### AsciiDocファイルの作成

`docs/` ディレクトリにAsciiDocファイル（`.adoc`）を配置します。

#### 基本的な設定例

```asciidoc
= ドキュメントタイトル
作成者名 <author@example.com>
v1.0, 2025-08-03
:doctype: book
:lang: ja
:toc: left
:toclevels: 3
:sectnums:
:kroki-server-url: http://localhost:8000
:source-highlighter: rouge
:pdf-themesdir: .
:pdf-theme: asciidoctor-pdf-theme

== セクション1

本文をここに記述します。
```

#### 図表の追加

**Mermaid図**
```asciidoc
[mermaid]
....
graph TD
    A[開始] --> B[処理]
    B --> C[終了]
....
```

**PlantUML図**
```asciidoc
[plantuml]
....
@startuml
Alice -> Bob: こんにちは
Bob --> Alice: こんにちは
@enduml
....
```

### GitHub Actionsでの自動化

リポジトリにプッシュすると、GitHub Actionsが自動的に実行され、PDFが生成されます。

生成されたPDFは「Artifacts」からダウンロードできます。

## 設定のカスタマイズ

### PDFテーマの変更

`asciidoctor-pdf-theme.yml` を編集することで、PDFの見た目をカスタマイズできます。

### 日本語フォントの変更

テーマファイル内の `font.catalog` セクションでフォントを変更できます：

```yaml
font:
  catalog:
    CustomFont:
      normal: /path/to/your/font.ttf
      bold: /path/to/your/font-bold.ttf
```

## トラブルシューティング

### Krokiサーバーに接続できない

```bash
# コンテナの状態を確認
podman ps

# コンテナを再起動
podman stop kroki
podman rm kroki
./scripts/setup-local.sh
```

### 日本語フォントが表示されない

- システムにNoto CJKフォントがインストールされているか確認
- テーマファイルのフォントパスが正しいか確認

### PDF生成に失敗する

```bash
# AsciiDoctorのバージョンを確認
asciidoctor --version
asciidoctor-pdf --version

# 必要なgemがインストールされているか確認
gem list | grep asciidoctor
```

## サポートしている図表フォーマット

Krokiを通じて以下の図表フォーマットをサポートしています：

- Mermaid
- PlantUML
- Graphviz (DOT)
- Ditaa
- Svgbob
- Vega
- Vega-Lite
- WaveDrom
- その他多数

詳細は [Kroki公式サイト](https://kroki.io/) を参照してください。

## ライセンス

このプロジェクトはMITライセンスの下で提供されています。