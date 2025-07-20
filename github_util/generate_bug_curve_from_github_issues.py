#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import json
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from github import Github

def get_token():
    """GitHub Actionsまたはローカル環境からトークンを取得"""
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        # ローカル環境の場合はファイルから読み込み
        home_dir = os.path.expanduser("~")
        token_path = Path(f"{home_dir}/.github/token.json")
        if token_path.exists():
            with open(token_path) as f:
                token = json.load(f)["token"]
        else:
            raise ValueError("GITHUB_TOKEN環境変数または~/.github/token.jsonを設定してください")
    
    return token

# 環境変数またはデフォルト値を使用
TOKEN = get_token()
OWNER = os.getenv("OWNER", "nsitexe")
REPO = os.getenv("REPO", "Design-SFM")
#OWNER = os.getenv("OWNER", "codecrafters-io")
#REPO = os.getenv("REPO", "build-your-own-x")

gh   = Github(TOKEN)
repo = gh.get_repo(f"{OWNER}/{REPO}")

def collect_issue_data():
    """Issue一覧を取得してデータフレームを作成"""
    issues = repo.get_issues(state="all")
    
    data = []
    for issue in issues:
        if issue.pull_request is not None:
            continue  # PR は除外
        labels = [label.name for label in issue.labels]
        # ラベルがない場合は"None"を追加
        if not labels:
            labels = ["None"]
        print(f"Issue: {issue.title}, Labels: {labels}")
        data.append({
            "created_at": issue.created_at.date(),
            "closed_at": issue.closed_at.date() if issue.closed_at else None,
            "labels": labels,
        })
    
    df = pd.DataFrame(data)
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    df["created_at"] = pd.to_datetime(df["created_at"])
    
    return df

def get_unique_labels(df):
    """ユニークなラベル一覧を取得"""
    all_labels = [label for labels_list in df["labels"] for label in labels_list]
    unique_labels = list(set(all_labels))
    # よく使われるラベル順にソート（頻度順）
    label_counts = pd.Series(all_labels).value_counts()
    return label_counts.index.tolist()

def create_label_timeline(df, unique_labels):
    """ラベル別のクローズ数を日付別に集計"""
    if df.empty:
        return pd.DataFrame()
    
    # 日付範囲を作成
    start_date = df["created_at"].min()
    end_date = df["closed_at"].max() if df["closed_at"].notnull().any() else df["created_at"].max()
    all_dates = pd.date_range(start_date, end_date)
    
    # ラベル別のクローズ数を集計
    timeline = pd.DataFrame(index=all_dates)
    
    for label in unique_labels:
        # そのラベルを持つクローズされたIssueを抽出
        label_issues = df[
            (df["labels"].apply(lambda x: label in x)) & 
            (df["closed_at"].notnull())
        ]
        
        if not label_issues.empty:
            closed_count = label_issues.groupby("closed_at").size()
            timeline[f"closed_{label}"] = closed_count
    
    # 欠損値を0で埋める
    timeline = timeline.fillna(0).astype(int)
    
    # 累積値を計算
    for label in unique_labels:
        col_name = f"closed_{label}"
        if col_name in timeline.columns:
            timeline[f"cumulative_{label}"] = timeline[col_name].cumsum()
    
    return timeline

def create_stacked_chart(df, timeline, unique_labels):
    """ラベル別の積み上げグラフを作成"""
    fig = go.Figure()
    
    # カラーパレット（ラベル数に応じて色を割り当て）
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]
    
    # 累積Issues（折れ線）
    total_created = df.groupby("created_at").size().cumsum()
    all_dates = pd.date_range(df["created_at"].min(), 
                              df["closed_at"].max() if df["closed_at"].notnull().any() else df["created_at"].max())
    total_timeline = pd.DataFrame(index=all_dates)
    total_timeline = total_timeline.join(total_created.rename("cumulative_issues"), how="left")
    total_timeline = total_timeline.fillna(method="ffill").fillna(0)
    
    fig.add_trace(
        go.Scatter(
            x=total_timeline.index,
            y=total_timeline["cumulative_issues"],
            name="累積 Issues",
            line=dict(color="black", width=3),
            mode="lines"
        )
    )
    
    # ラベル別の累積クローズIssues（積み上げ棒グラフ）
    for i, label in enumerate(unique_labels):
        col_name = f"cumulative_{label}"
        if col_name in timeline.columns:
            fig.add_trace(
                go.Bar(
                    x=timeline.index,
                    y=timeline[col_name],
                    name=f"{label}",
                    marker_color=colors[i % len(colors)],
                    opacity=0.8
                )
            )
    
    fig.update_layout(
        title=dict(text=f"Bug Curve {REPO} - ラベル別積み上げ", x=0.5, y=0.95, font=dict(size=20)),
        xaxis_title="Date",
        yaxis_title="Count",
        legend=dict(x=0, y=1.0),
        barmode="stack",  # 積み上げモード
        template="plotly_white",
        width=1200,
        height=700,
    )
    
    return fig

def main():
    """メイン処理"""
    try:
        print(f"Repository: {OWNER}/{REPO}")
        
        # データ収集
        df = collect_issue_data()
        print(f"Total issues: {len(df)}")
        
        if df.empty:
            print("No issues found")
            return
        
        # ラベル取得
        unique_labels = get_unique_labels(df)
        print(f"Unique labels: {unique_labels}")
        
        # タイムライン作成
        timeline = create_label_timeline(df, unique_labels)
        
        # グラフ作成
        fig = create_stacked_chart(df, timeline, unique_labels)
        
        # HTMLファイル保存
        output_file = f"{REPO}_bug_curve_stacked.html"
        
        # GitHub Actions環境対応
        if os.getenv("GITHUB_ACTIONS"):
            output_file = "bug_curve_stacked.html"
        
        pio.write_html(
            fig,
            file=output_file,
            auto_open=False,
            include_plotlyjs="cdn",
            config={
                "displaylogo": False,
                "displayModeBar": True,
                "responsive": True,
            },
        )
        
        print(f"Bug curve saved to {output_file}")
        
        # CSVも保存
        timeline.to_csv(f"{REPO}_timeline_stacked.csv", index=True, index_label="date")
        df.to_csv(f"{REPO}_issues.csv", index=False)
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
