# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

このプロジェクトはGitHubのIssueとProjectデータからガントチャートを生成するPythonユーティリティです。Plotlyを使用してタイムライン形式のガントチャートを描画し、ベースラインと実績を並列表示できます。

## 依存関係

- Python 3.13+
- requests: GitHub API アクセス
- pandas: データ操作とCSV処理
- plotly: インタラクティブなガントチャート生成

依存関係をインストール:
```bash
pip install -r requirements.txt
```

## 実行方法

1. GitHub Personal Access Tokenを環境変数に設定:
```bash
export GITHUB_TOKEN=your_token_here
```

2. スクリプト内のパラメータを設定:
- `owner`: GitHubユーザー名
- `repo`: リポジトリ名  
- `project_number`: プロジェクト番号

3. 実行:
```bash
python3 draw_gantt_from_issue_and_project.py
```

## コード構造

現在のスクリプトはサンプルデータでガントチャートの生成デモを行っています。実際のGitHub APIとの連携やデータ処理ロジックを追加する場合は、以下の構造を考慮してください：

- データ取得層: GitHub API からIssueとProjectデータを取得
- データ変換層: APIレスポンスをplotly用のDataFrameに変換
- 可視化層: ガントチャートの生成とカスタマイズ