#!/usr/bin/env python3
"""
GitHub Organization Repository Transfer Tool

GitHubのorganization変更に伴うリポジトリ移動を自動化するツール
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import click
import requests
from github import Github, Repository
from tabulate import tabulate
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transfer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TransferResult:
    """転送結果を保持するデータクラス"""
    repo_name: str
    success: bool
    error_message: Optional[str] = None
    transfer_time: Optional[datetime] = None

class GitHubOrgTransfer:
    """GitHub organization間でのリポジトリ転送を管理するクラス"""
    
    def __init__(self, token: str):
        """
        初期化
        
        Args:
            token: GitHub Personal Access Token
        """
        self.token = token
        self.github = Github(token)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        })
        
    def get_organization_repos(self, org_name: str) -> List[Repository.Repository]:
        """
        指定されたorganizationの全リポジトリを取得
        
        Args:
            org_name: organization名
            
        Returns:
            リポジトリのリスト
        """
        try:
            org = self.github.get_organization(org_name)
            repos = list(org.get_repos())
            logger.info(f"Organization '{org_name}'から{len(repos)}個のリポジトリを取得しました")
            return repos
        except Exception as e:
            logger.error(f"Organization '{org_name}'のリポジトリ取得に失敗: {e}")
            return []
    
    def check_transfer_eligibility(self, repo: Repository.Repository, target_org: str) -> Tuple[bool, str]:
        """
        リポジトリの転送可能性をチェック
        
        Args:
            repo: チェック対象のリポジトリ
            target_org: 転送先organization
            
        Returns:
            (転送可能かどうか, 理由/エラーメッセージ)
        """
        # フォークの場合は転送不可
        if repo.fork:
            return False, "フォークされたリポジトリは転送できません（GitHubの制限）"
        
        # 同名リポジトリの存在チェック
        try:
            target_org_obj = self.github.get_organization(target_org)
            try:
                existing_repo = target_org_obj.get_repo(repo.name)
                return False, f"転送先に同名のリポジトリ '{repo.name}' が既に存在します"
            except:
                pass  # 同名リポジトリが存在しない（転送可能）
        except Exception as e:
            return False, f"転送先organization '{target_org}'へのアクセス権限がありません: {e}"
        
        # 管理者権限チェック
        try:
            permissions = repo.get_collaborator_permission(self.github.get_user().login)
            if permissions != 'admin':
                return False, f"リポジトリ '{repo.name}' への管理者権限が必要です（現在: {permissions}）"
        except Exception as e:
            return False, f"権限確認エラー: {e}"
        
        # プライベートリポジトリの場合の注意事項
        warning = ""
        if repo.private:
            warning = " (注意: プライベートリポジトリの機能は転送先アカウントのプランに依存します)"
        
        return True, f"転送可能です{warning}"
    
    def transfer_repository(self, repo: Repository.Repository, target_org: str, 
                          dry_run: bool = False) -> TransferResult:
        """
        リポジトリを指定されたorganizationに転送
        
        Args:
            repo: 転送対象のリポジトリ
            target_org: 転送先organization
            dry_run: ドライランモード（実際の転送は行わない）
            
        Returns:
            転送結果
        """
        start_time = datetime.now()
        
        # 転送可能性チェック
        can_transfer, reason = self.check_transfer_eligibility(repo, target_org)
        if not can_transfer:
            logger.warning(f"リポジトリ '{repo.name}' の転送をスキップ: {reason}")
            return TransferResult(repo.name, False, reason)
        
        if dry_run:
            logger.info(f"[DRY RUN] リポジトリ '{repo.name}' を '{target_org}' に転送します")
            return TransferResult(repo.name, True, "ドライランモード", start_time)
        
        try:
            # GitHub APIを使用してリポジトリを転送
            # 注意: Repository Transfer APIを使用
            url = f"https://api.github.com/repos/{repo.full_name}/transfer"
            headers = {
                'Accept': 'application/vnd.github.nightshade-preview+json',  # Transfer API用ヘッダー
                'Authorization': f'token {self.token}'
            }
            data = {
                "new_owner": target_org,
                "team_ids": []  # 必要に応じてチームIDを指定
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 202:  # Accepted
                logger.info(f"リポジトリ '{repo.name}' の転送を開始しました")
                
                # 転送完了の待機（オプション）
                if self._wait_for_transfer_completion(repo.full_name, target_org):
                    logger.info(f"リポジトリ '{repo.name}' の転送が完了しました")
                    return TransferResult(repo.name, True, None, start_time)
                else:
                    return TransferResult(repo.name, False, "転送のタイムアウト")
            else:
                error_msg = f"転送API呼び出しエラー: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return TransferResult(repo.name, False, error_msg)
                
        except Exception as e:
            error_msg = f"転送中にエラーが発生: {e}"
            logger.error(error_msg)
            return TransferResult(repo.name, False, error_msg)
    
    def _wait_for_transfer_completion(self, old_repo_path: str, target_org: str, 
                                    timeout: int = 300) -> bool:
        """
        転送完了を待機
        
        Args:
            old_repo_path: 元のリポジトリパス
            target_org: 転送先organization
            timeout: タイムアウト時間（秒）
            
        Returns:
            転送完了したかどうか
        """
        repo_name = old_repo_path.split('/')[-1]
        new_repo_path = f"{target_org}/{repo_name}"
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 新しい場所でリポジトリが存在するかチェック
                response = self.session.get(f"https://api.github.com/repos/{new_repo_path}")
                if response.status_code == 200:
                    return True
                time.sleep(10)  # 10秒待機
            except Exception:
                time.sleep(10)
        
        return False
    
    def batch_transfer(self, source_org: str, target_org: str, 
                      repo_filter: Optional[List[str]] = None,
                      dry_run: bool = False) -> List[TransferResult]:
        """
        複数リポジトリの一括転送
        
        Args:
            source_org: 転送元organization
            target_org: 転送先organization
            repo_filter: 転送対象リポジトリ名のリスト（Noneの場合は全て）
            dry_run: ドライランモード
            
        Returns:
            転送結果のリスト
        """
        logger.info(f"一括転送開始: {source_org} -> {target_org}")
        
        # リポジトリ一覧取得
        repos = self.get_organization_repos(source_org)
        
        # フィルタリング
        if repo_filter:
            repos = [repo for repo in repos if repo.name in repo_filter]
            logger.info(f"フィルタ適用後: {len(repos)}個のリポジトリ")
        
        results = []
        for i, repo in enumerate(repos, 1):
            logger.info(f"処理中 ({i}/{len(repos)}): {repo.name}")
            
            result = self.transfer_repository(repo, target_org, dry_run)
            results.append(result)
            
            # レート制限対策（少し待機）
            if not dry_run:
                time.sleep(2)
        
        return results
    
    def generate_report(self, results: List[TransferResult]) -> str:
        """
        転送結果のレポートを生成
        
        Args:
            results: 転送結果のリスト
            
        Returns:
            レポート文字列
        """
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        
        # 成功・失敗の統計
        report = f"\n=== 転送結果レポート ===\n"
        report += f"総処理数: {len(results)}\n"
        report += f"成功: {success_count}\n"
        report += f"失敗: {fail_count}\n\n"
        
        # 詳細テーブル
        table_data = []
        for result in results:
            status = "✅ 成功" if result.success else "❌ 失敗"
            error = result.error_message or "-"
            table_data.append([result.repo_name, status, error])
        
        report += tabulate(
            table_data,
            headers=["リポジトリ名", "ステータス", "エラー/メモ"],
            tablefmt="grid"
        )
        
        return report

@click.group()
def cli():
    """GitHub Organization Repository Transfer Tool"""
    pass

@cli.command()
@click.option('--source-org', required=True, help='転送元organization名')
@click.option('--target-org', required=True, help='転送先organization名')
@click.option('--repos', help='転送対象リポジトリ名（カンマ区切り）')
@click.option('--dry-run', is_flag=True, help='ドライランモード（実際の転送は行わない）')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub Personal Access Token')
def transfer(source_org: str, target_org: str, repos: Optional[str], 
            dry_run: bool, token: str):
    """リポジトリの転送を実行"""
    
    if not token:
        click.echo("エラー: GitHub tokenが必要です。環境変数GITHUB_TOKENまたは--tokenで指定してください。")
        return
    
    # リポジトリフィルタの解析
    repo_filter = None
    if repos:
        repo_filter = [name.strip() for name in repos.split(',')]
    
    try:
        transfer_tool = GitHubOrgTransfer(token)
        
        if dry_run:
            click.echo(f"🔍 ドライランモード: {source_org} -> {target_org}")
        else:
            click.echo(f"🚀 転送開始: {source_org} -> {target_org}")
        
        # 転送実行
        results = transfer_tool.batch_transfer(
            source_org, target_org, repo_filter, dry_run
        )
        
        # レポート生成・表示
        report = transfer_tool.generate_report(results)
        click.echo(report)
        
        # レポートをファイルに保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"transfer_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        click.echo(f"\n📊 レポートを {report_file} に保存しました")
        
    except Exception as e:
        logger.error(f"転送処理中にエラーが発生: {e}")
        click.echo(f"❌ エラー: {e}")

@cli.command()
@click.option('--org', required=True, help='organization名')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub Personal Access Token')
def list_repos(org: str, token: str):
    """organizationのリポジトリ一覧を表示"""
    
    if not token:
        click.echo("エラー: GitHub tokenが必要です。")
        return
    
    try:
        transfer_tool = GitHubOrgTransfer(token)
        repos = transfer_tool.get_organization_repos(org)
        
        table_data = []
        for repo in repos:
            visibility = "🔒 Private" if repo.private else "🌐 Public"
            fork_status = "🍴 Fork" if repo.fork else "📦 Original"
            table_data.append([repo.name, visibility, fork_status, repo.size])
        
        click.echo(f"\n📁 Organization '{org}' のリポジトリ一覧:")
        click.echo(tabulate(
            table_data,
            headers=["名前", "可視性", "タイプ", "サイズ(KB)"],
            tablefmt="grid"
        ))
        
    except Exception as e:
        logger.error(f"リポジトリ一覧取得エラー: {e}")
        click.echo(f"❌ エラー: {e}")

if __name__ == '__main__':
    cli()