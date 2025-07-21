# GitHub Organization Repository Transfer Tool

GitHub organizationの変更に伴うリポジトリ移動を自動化するツールです。

## 概要

このツールは以下の機能を提供します：
- 複数リポジトリの一括転送
- 転送前の適格性チェック
- 転送状況の監視
- 詳細なログとレポート生成
- ドライランモード

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成し、GitHub Personal Access Tokenを設定してください。

```bash
cp .env.example .env
```

必要な権限：
- `repo` (すべて)
- `admin:org` (read:org)
- `user` (read:user)

## 使用方法

### リポジトリ一覧の確認

```bash
python github_org_transfer.py list-repos --org your-org-name
```

### 転送の実行

#### 全リポジトリの転送（ドライラン）
```bash
python github_org_transfer.py transfer \
  --source-org source-org \
  --target-org target-org \
  --dry-run
```

#### 特定リポジトリの転送
```bash
python github_org_transfer.py transfer \
  --source-org source-org \
  --target-org target-org \
  --repos "repo1,repo2,repo3"
```

#### 実際の転送実行
```bash
python github_org_transfer.py transfer \
  --source-org source-org \
  --target-org target-org
```

## ⚠️ 重要: 手動転送を強く推奨

**本番環境や重要なリポジトリの転送は手動実施を強く推奨します。**

詳細は `manual_transfer_guide.md` を参照してください。

### GitHub APIの制限
- Repository Transfer APIはプレビュー版
- レート制限: 通常5,000 requests/hour
- 管理者権限が必要
- GitHub.com間でのみ転送可能

### 転送できないリポジトリ
- フォークされたリポジトリ（GitHub の仕様）
- 同名のリポジトリが転送先に既に存在する場合
- 管理者権限がないリポジトリ

### 転送時の注意点
- 元の所有者は自動的にコラボレーターになります
- Issue/PRの割り当てが変更される可能性があります
- 一部機能は転送先アカウントの購読プランに依存します
- Personal account への転送は24時間以内の確認が必要
- Read-only collaborators は personal account に転送されません

## ファイル構成

- `github_org_transfer.py` - メインスクリプト
- `analysis.md` - 分析結果とドキュメント
- `requirements.txt` - Python依存関係
- `.env.example` - 環境変数テンプレート
- `transfer.log` - 実行ログ
- `transfer_report_*.txt` - 転送結果レポート

## トラブルシューティング

### よくあるエラー

1. **権限エラー**
   - Personal Access Tokenの権限を確認
   - 転送先organizationへのアクセス権を確認

2. **レート制限**
   - 実行間隔を長くする
   - 少数ずつ転送する

3. **転送失敗**
   - ログファイルで詳細を確認
   - フォークや同名リポジトリをチェック

## セキュリティ考慮事項

- Personal Access Tokenは適切に管理してください
- `.env`ファイルはgitで管理しないでください
- 転送前には必ずバックアップを取ってください

## ライセンス

このツールは教育・研究目的で提供されています。実際の本番環境での使用前には十分にテストしてください。