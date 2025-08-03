#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import pytz
import requests


class GitHubGanttChart:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_project_items(
        self, owner: str, repo: str, project_number: int
    ) -> List[Dict]:
        """GitHubプロジェクトからアイテム一覧を取得"""
        # GraphQL APIを使用してプロジェクトデータを取得
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            projectV2(number: $number) {
              items(first: 100) {
                nodes {
                  id
                  content {
                    ... on Issue {
                      number
                      title
                      body
                      assignees(first: 10) {
                        nodes {
                          login
                        }
                      }
                    }
                  }
                  fieldValues(first: 20) {
                    nodes {
                      ... on ProjectV2ItemFieldDateValue {
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                        date
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.headers,
            json={
                "query": query,
                "variables": {"owner": owner, "repo": repo, "number": project_number},
            },
        )

        if response.status_code == 200:
            json_response = response.json()

            # エラーチェックを追加
            if "errors" in json_response:
                print("GraphQL APIエラー:")
                for error in json_response["errors"]:
                    print(f"- {error.get('message', 'Unknown error')}")
                raise Exception("GraphQL APIでエラーが発生しました")

            # データの存在確認
            if not json_response.get("data"):
                print("レスポンス:", json_response)
                raise Exception("APIレスポンスにデータが含まれていません")

            try:
                return json_response["data"]["repository"]["projectV2"]["items"][
                    "nodes"
                ]
            except (KeyError, TypeError) as e:
                print("レスポンス:", json_response)
                raise Exception(f"予期しない形式のレスポンス: {str(e)}")
        else:
            raise Exception(
                f"GitHub API error: {response.status_code} - {response.text}"
            )

    def parse_roadmap_json(self, issue_body: str) -> Optional[Dict]:
        """Issue説明からRoadmapのJSONを抽出"""
        # ### Roadmapの後に続くJSONを探す
        patterns = [
            # コードブロック内のJSONパターン
            r"```[\s]*Roadmap[s]*\s*\njson\s*\n([\s\S]*?)\n```",
            # 直接JSONが書かれているパターン
            r"Roadmap\s*\n([\s\S]*?})",
            # 改行があるJSONパターン
            r"```[\s]*Roadmap[s]*\s*\n([\s\S]*?)\n```",
            # より柔軟なパターン（Baseline_Start_DateとBaseline_End_Dateを含む）
            r"Roadmap[\s\S]*?({[\s\S]*\"Baseline_Start_Date\"[\s\S]*\"Baseline_End_Date\"[\s\S]*})",
        ]

        for pattern in patterns:
            match = re.search(pattern, issue_body, re.MULTILINE | re.DOTALL)
            if match:
                json_str = match.group(1)

                # 余分な改行や空白を整理
                json_str = re.sub(r"\s*:\s*", ":", json_str)
                json_str = re.sub(r"\s*,\s*", ",", json_str)

                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # デバッグ用に抽出されたJSON文字列を出力
                    print(f"JSONパースエラー: {json_str}")
                    continue

        return None

    def extract_dates_from_project_item(
        self, item: Dict
    ) -> Tuple[Optional[str], Optional[str]]:
        """プロジェクトアイテムからstart dateとend dateを抽出"""
        start_date: Optional[str] = None
        end_date: Optional[str] = None

        for field_value in item.get("fieldValues", {}).get("nodes", []):
            field_name = field_value.get("field", {}).get("name", "")
            if field_name.lower() in ("start date", "start"):
                start_date = field_value.get("date")
            elif field_name.lower() in ("end date", "end", "due date", "due"):
                end_date = field_value.get("date")

        return start_date, end_date

    def create_gantt_data(
        self, df: pd.DataFrame, repo: str, owner: str
    ) -> pd.DataFrame:
        """データをガントチャート用のデータへ構築"""
        if df.empty:
            print("データが見つかりませんでした")
            return

        # プロセス管理No(issueタイトルの*-*-*の前半)を抽出
        df["process_number"] = df["issue"].str.split(" ").str[0]

        # issueタイトルの*-*-＊部分以外を抽出
        df["issue_title"] = df["issue"].str.split(" ").str[1:].str.join(" ")

        # issue列をホバー用にコピー
        df["issue_hover"] = df["issue"].str.replace(" <", "<br><")

        # y軸表示用のissue列を加工
        def format_issue_title(x: str) -> str:
            parts = x.split(" <", 1)  # 最初の '（' で分割
            if len(parts) == 2:
                first_part = parts[0][:20] + ("..." if len(parts[0]) > 20 else "")
                second_part = parts[1][:20] + ("..." if len(parts[1]) > 20 else "")
                return f"{first_part}<br>{second_part}"
            return x[:20] + ("..." if len(x) > 20 else "")

        # issue_title列を2行表示に加工
        df["issue_title"] = df["issue_title"].apply(format_issue_title)

        # 日付フォーマットを作成
        df["date_text"] = (
            df["start"].dt.strftime("%m/%d") + " - " + df["end"].dt.strftime("%m/%d")
        )

        # issueへのリンクを作成
        df["issue_url"] = (
            '<a href="https://github.com/{owner}/{repo}/issues/'
            + df["number"].astype(str)
            + '" target="_blank">'
            + df["issue_title"]
            + "</a>"
        )

        # issue_urlの頭に、process_numberを追加
        df["issue_url"] = df["process_number"] + " " + df["issue_url"]

        # typeカテゴリの順序を指定してActualを上に表示
        df["type"] = pd.Categorical(
            df["type"], categories=["Baseline", "Actual"], ordered=True
        )

        # issueでsort
        df = df.sort_values("issue", ascending=True)

        return df

    def issues_to_gantt_data(
        self, owner: str, repo: str, project_number: int
    ) -> pd.DataFrame:
        """GitHubプロジェクトやIssueからデータを作成"""
        items = self.get_project_items(owner, repo, project_number)
        data: List[Dict] = []

        for item in items:
            content = item.get("content")
            if not content:
                continue

            issue_title = content.get("title", "")
            issue_body = content.get("body", "")
            issue_number = content.get("number")
            assignees = (
                [a.get("login") for a in content.get("assignees", {}).get("nodes", [])]
                if content.get("assignees")
                else []
            )

            # issue_numberが存在しない場合はスキップ
            if not issue_number:
                continue

            # 安全な文字列結合
            issue_label = f"{issue_title}"

            # Actualデータ（プロジェクトから）
            actual_start, actual_end = self.extract_dates_from_project_item(item)

            # 今日の日付を取得
            # today = date.today()
            today = datetime.now(pytz.timezone("Asia/Tokyo")).date()
            ongoing = False

            if actual_start:
                if actual_end is None:
                    actual_end = today
                    ongoing = True

                data.append(
                    {
                        "issue": issue_label,
                        "type": "Actual",
                        "start": actual_start,
                        "end": actual_end,
                        "assignees": ", ".join(assignees),
                        "number": issue_number,
                        "ongoing": ongoing,
                    }
                )

            # Baselineデータ（Issueのbodyから）
            roadmap_data = self.parse_roadmap_json(issue_body)
            if roadmap_data:
                baseline_start = roadmap_data.get("Baseline_Start_Date")
                baseline_end = roadmap_data.get("Baseline_End_Date")

                if baseline_start and baseline_end:
                    data.append(
                        {
                            "issue": issue_label,
                            "type": "Baseline",
                            "start": baseline_start,
                            "end": baseline_end,
                            "assignees": ", ".join(assignees),
                            "number": issue_number,
                            "ongoing": False,
                        }
                    )

        df = pd.DataFrame(data)
        if not df.empty:
            df["start"] = pd.to_datetime(df["start"]).dt.tz_localize("Asia/Tokyo")
            df["end"] = pd.to_datetime(df["end"]).dt.tz_localize("Asia/Tokyo")
            # issueでソート
            df = df.sort_values("issue", ascending=True)

        return df

    def create_gantt_chart(self, df: pd.DataFrame, repo: str, owner: str) -> None:
        """二重線ガントチャートを作成"""

        # 1. 明度差セット（推奨）
        color_pairs = [
            {"Baseline": "#BBDEFB", "Actual": "#1E88E5"},  # 薄青 → 濃青
            {"Baseline": "#FFEBEE", "Actual": "#FF8F00"},  # 薄桜 → 濃橙
            {"Baseline": "#E8F5E9", "Actual": "#4CAF50"},  # 薄緑 → 緑
            {"Baseline": "#FCE4EC", "Actual": "#9E1E63"},  # 薄ピンク → 濃ピンク
            {"Baseline": "#F3E5F5", "Actual": "#9C27B0"},  # 薄紫 → 濃紫
        ]

        # 2. 補色寄りセット
        color_pairs = [
            {"Baseline": "#B0BEC5", "Actual": "#FF5722"},  # グレー → 暖色赤
            {"Baseline": "#CFD8DC", "Actual": "#2196F3"},  # グレー → 寒色青
            {"Baseline": "#F5F5F5", "Actual": "#4CAF50"},  # 薄グレー → 緑
            {"Baseline": "#ECEFF1", "Actual": "#FF9800"},  # 薄グレー → 橙
            {"Baseline": "#FAFAFA", "Actual": "#9C27B0"},  # 薄グレー → 紫
        ]

        # 3. パステル＋ビビッドセット
        color_pairs = [
            {"Baseline": "#FDC0D2", "Actual": "#D32F2F"},  # パステル赤 → ビビッド赤
            {"Baseline": "#C8E6C9", "Actual": "#388E3C"},  # パステル緑 → ビビッド緑
            {"Baseline": "#BBDEFB", "Actual": "#1976D2"},  # パステル青 → ビビッド青
            {"Baseline": "#FFE0B2", "Actual": "#F57C00"},  # パステル橙 → ビビッド橙
            {"Baseline": "#E1BEE7", "Actual": "#7B1FA2"},  # パステル紫 → ビビッド紫
        ]

        # 色セットの選択（明度差セット）
        color_map = {
            "Baseline": "#BBDEFB",
            "Actual": "#1E88E5",
        }  # Baselineを少し濃い青に変更

        # 完了したIssueとongoingのカラーマップを作成
        completed_color_map = {
            "Baseline": "#F5F5F5",  # グレースケール（薄い）
            "Actual": "#9E9E9E",  # グレースケール（濃い）
        }
        ongoing_color = "#FFB74D"  # 薄めのオレンジ色（#FFA726 より薄い）

        fig = px.timeline(
            df,
            x_start="start",
            x_end="end",
            y="issue_url",
            color="type",
            text="date_text",
            color_discrete_map=color_map,
            category_orders={"type": ["Actual", "Baseline"]},
            hover_data={
                "issue": False,
                "issue_title": False,
                "issue_url": False,
                "issue_hover": True,  # フルタイトルを表示
                "start": True,
                "end": True,
                "type": True,
                "date_text": False,
                "assignees": True,
            },
        )

        # 今日の日付を取得
        today = datetime.now(pytz.timezone("Asia/Tokyo")).date()

        # 完了したIssueを判定（Actualのend_dateが今日より過去）
        completed_issues: List[str] = []
        ongoing_issues: List[str] = []
        for issue in df[df["type"] == "Actual"]["issue_url"].unique():
            issue_data = df[(df["type"] == "Actual") & (df["issue_url"] == issue)].iloc[
                0
            ]
            end_date = issue_data["end"].date()
            if issue_data["ongoing"]:
                ongoing_issues.append(issue)
            elif end_date <= today:
                completed_issues.append(issue)

        # データフレームに 'color_set' 列を追加
        df["color_set"] = np.where(
            df["issue_url"].isin(completed_issues),
            "completed",
            np.where(df["issue_url"].isin(ongoing_issues), "ongoing", "active"),
        )

        # Issueの色を変更（完了/進行中/アクティブ）
        for trace in fig.data:
            if trace.name == "Baseline":
                mask = [issue in completed_issues for issue in trace.y]
                trace.marker.color = [
                    completed_color_map["Baseline"] if m else color_map["Baseline"]
                    for m in mask
                ]
            else:  # Actual
                trace.marker.color = [
                    completed_color_map["Actual"]
                    if issue in completed_issues
                    else (
                        ongoing_color
                        if issue in ongoing_issues
                        else color_map["Actual"]
                    )
                    for issue in trace.y
                ]

        fig.update_layout(
            barmode="group",
            bargap=0.1,
            bargroupgap=0.2,
            title="GitHub Project Gantt Chart (Baseline vs Actual)",
            height=max(len(df["issue"].unique()) * 70, 400),
            showlegend=False,
            yaxis=dict(
                categoryorder="category descending",
            ),
            xaxis=dict(
                title="日付",
                showgrid=True,
                gridwidth=1,
                gridcolor="lightgray",
                griddash="dot",
                tickformat="%Y-%m-%d",
                rangeslider=dict(visible=True),
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(
                                count=1,
                                label="1ヶ月",
                                step="month",
                                stepmode="backward",
                            ),
                            dict(
                                count=3,
                                label="3ヶ月",
                                step="month",
                                stepmode="backward",
                            ),
                            dict(
                                count=1, label="1年", step="year", stepmode="backward"
                            ),
                            dict(step="all", label="全期間"),
                        ]
                    )
                ),
            ),
            yaxis_title="Issue",
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        fig.update_traces(width=0.32)

        # issueごとに薄いグレーの横線を追加
        unique_issues = df["issue"].unique()
        for i, issue in enumerate(unique_issues):
            if i > 0:  # 最初のissue以外に横線を追加
                fig.add_hline(
                    y=i - 0.5, line_width=1, line_color="lightgray", opacity=0.3
                )

        # 今日の日付に赤い縦線を追加
        today = datetime.now().strftime("%Y-%m-%d")

        fig.add_vline(
            x=today,
            line_width=3,
            line_color="red",
        )

        fig.add_annotation(
            x=today,
            y=1.10,
            yref="paper",
            text="Today",
            showarrow=False,
            font=dict(color="red", size=12, family="Arial Black"),
        )

        fig.write_html(
            f"{repo}_gantt_chart.html",
            include_plotlyjs="cdn",
            config={"displaylogo": False, "displayModeBar": False, "responsive": True},
        )
        print(f"ガントチャートを{repo}_gantt_chart.htmlに保存しました")


def main():
    # GitHub Actionsまたはローカル環境からトークンを取得
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        # ローカル環境の場合はファイルから読み込み
        path = Path("~/.github/token.json").expanduser()
        if path.exists():
            with path.open(encoding="utf-8") as f:
                token = json.load(f)["token"]
        else:
            print("GITHUB_TOKEN環境変数または~/.github/token.jsonを設定してください")
            return

    # 環境変数またはデフォルト値を使用
    owner = os.getenv("OWNER", "tfukuda675")
    repo = os.getenv("REPO", "my_todo")
    project_number = int(os.getenv("PROJECT_NUMBER", "4"))

    try:
        chart = GitHubGanttChart(token)
        df = chart.issues_to_gantt_data(owner, repo, project_number)
        df = chart.create_gantt_data(df, repo, owner)
        chart.create_gantt_chart(df, repo, owner)
    except Exception as e:
        import traceback

        print(f"エラーが発生しました: {e}")
        print("詳細なトレースバック:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
