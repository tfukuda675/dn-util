#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import json
import os

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from github import Github

home_dir = os.path.expanduser("~")
with open(f"{home_dir}/.github/token.json") as f:
    TOKEN = json.load(f)["token"]

OWNER = "nsitexe"
REPO  = "Design-SFM"

gh   = Github(TOKEN)
repo = gh.get_repo(f"{OWNER}/{REPO}")

# Issue 一覧を取得
issues = repo.get_issues(state="all")

data = []
for issue in issues:
    if issue.pull_request is not None:
        continue  # PR は除外
    labels = [label.name for label in issue.labels]
    print(f"Issue: {issue.title}, Labels: {labels}")
    data.append(
        {
            "created_at": issue.created_at.date(),
            "closed_at": issue.closed_at.date() if issue.closed_at else None,
            "labels": labels,
        }
    )

df = pd.DataFrame(data)

# 全 Tag を取得
all_labels = [label for labels_list in df["labels"] for label in labels_list]

# ユニークなラベル一覧を取得
unique_labels = set(all_labels)

# label でフィルタしない all を追加
unique_labels.add("all")

# closed_at 列を datetime 型に変換
df["closed_at"] = pd.to_datetime(df["closed_at"])
df["created_at"] = pd.to_datetime(df["created_at"])


# 日付の範囲を作成
all_dates = pd.date_range(
    df["created_at"].min(),
    df["closed_at"].max() if df["closed_at"].notnull().any() else df["created_at"].max()
)

for label in unique_labels:
    if label == "all":
        df_label = df.copy()
    else:
        df_label = df[df["labels"].apply(lambda x: label in x)]

    # 日付ごとに新規・クローズ数を集計
    created_count = df_label.groupby("created_at").size().rename("created")
    closed_count  = (
        df_label.dropna(subset=["closed_at"])
                .groupby("closed_at").size().rename("closed")
    )

    # CSV に保存（Issues 一覧）
    if label == "all":
        df_label.to_csv(f"{REPO}_issues.csv", index=False)
    else:
        df_label.to_csv(f"{REPO}_issues_label_{label}.csv", index=False)

    # 日付ごとに新規・クローズ数を結合
    timeline = pd.DataFrame(index=all_dates)
    timeline = (
        timeline.join(created_count, how="left")
                .join(closed_count,  how="left")
    )

    # 累積バグ数 (open 数) を計算
    timeline["cumulative_issue"]   = timeline["created"].cumsum()
    timeline["cumulative_closed"]  = timeline["closed"].cumsum()

    # int 型に整形（欠損は 0 扱い）
    timeline["created"]            = timeline["created"].astype(int)
    timeline["closed"]             = timeline["closed"].astype(int)
    timeline["cumulative_issue"]   = timeline["cumulative_issue"].astype(int)
    timeline["cumulative_closed"]  = timeline["cumulative_closed"].astype(int)

    # CSV に保存（Timeline）
    if label == "all":
        timeline.to_csv(f"{REPO}_timeline.csv", index=True, index_label="date")
    else:
        timeline.to_csv(f"{REPO}_timeline_label_{label}.csv", index=True, index_label="date")

    # グラフ描画
    fig = go.Figure()


    if label == "all":
        # 累積Issues（折れ線）
        fig.add_trace(
            go.Scatter(
                x=timeline.index,
                y=timeline["cumulative_issue"],
                name="累積 Issues",
            )
        )

        # 累積Closed Issues（棒グラフ）
        fig.add_trace(
            go.Bar(
                x=timeline.index,
                y=timeline["cumulative_closed"],
                name="累積 Closed Issues",
                marker_color="red",
                opacity=0.3,
            )
        )

        fig.update_layout(
            title=dict(text=f"Bug Curve {REPO}", x=0.5, y=0.95, font=dict(size=20)),
            xaxis_title="Date",
            yaxis_title="Count",
            legend=dict(x=0, y=1.0),
            barmode="overlay",
            template="plotly_white",
            width=1000,
            height=600,
        )

        pio.write_html(
            fig,
            file=f"{REPO}_bug_curve.html",
            auto_open=False,
            include_plotlyjs="cdn",
            config={
                "displaylogo": False,
                "displayModeBar": False,
                "responsive": True,
            },
        )


        # 累積Issues（折れ線）
        fig.add_trace(
            go.Scatter(
                x=timeline.index,
                y=timeline["cumulative_issue"],
                mode="lines",
            )
        )

        # 累積Closed Issues（棒グラフ）
        fig.add_trace(
            go.Bar(
                x=timeline.index,
                y=timeline["cumulative_closed"],
                name=f"累積 Closed Issues Label {label}",
                marker_color="red",
                opacity=0.3,
            )
        )

        fig.update_layout(
            title=dict(text=f"Bug Curve {REPO} Label {label}", x=0.5, y=0.95, font=dict(size=20)),
            xaxis_title="Date",
            yaxis_title="Count",
            legend=dict(x=0, y=1.0),
            barmode="overlay",
            template="plotly_white",
            width=1000,
            height=600,
        )

        pio.write_html(
            fig,
            file=f"{REPO}_bug_curve_label_{label}.html",
            auto_open=False,
            include_plotlyjs="cdn",
            config={
                "displaylogo": False,
                "displayModeBar": False,
                "responsive": True,
            },
        )
