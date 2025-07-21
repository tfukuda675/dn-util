"""
設定ファイル - GitHub Organization Transfer Tool
"""

import os
from typing import Dict, Any

# GitHub API設定
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_ACCEPT_HEADER = "application/vnd.github.v3+json"

# レート制限設定
DEFAULT_RATE_LIMIT_DELAY = int(os.getenv('RATE_LIMIT_DELAY', '2'))  # 秒
TRANSFER_TIMEOUT = int(os.getenv('TRANSFER_TIMEOUT', '300'))  # 秒

# 必要なGitHub権限
REQUIRED_SCOPES = [
    'repo',           # リポジトリへのフルアクセス
    'admin:org',      # Organization管理
    'user'            # ユーザー情報読み取り
]

# 転送可能性チェック設定
TRANSFER_ELIGIBILITY_CHECKS = {
    'check_fork_status': True,      # フォークかどうかチェック
    'check_private_access': True,   # プライベートリポジトリアクセスチェック
    'check_size_limit': True,       # サイズ制限チェック
    'check_lfs_usage': True,        # Git LFS使用状況チェック
}

# サイズ制限（MB）
MAX_REPO_SIZE_MB = 1000

# ログ設定
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': 'transfer.log',
    'encoding': 'utf-8'
}

# 除外するリポジトリパターン
EXCLUDED_REPO_PATTERNS = [
    r'.*\.github\.io$',     # GitHub Pagesリポジトリ
    r'^\.github$',          # .githubリポジトリ
    r'.*-archived$',        # アーカイブされたリポジトリ
]

# 転送時の確認プロンプト
CONFIRMATION_PROMPTS = {
    'dangerous_repos': [
        'main',
        'master', 
        'production',
        'prod'
    ],
    'large_repos_mb': 100
}