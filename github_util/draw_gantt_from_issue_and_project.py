#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.io as pio
import requests

pio.renderers.default = "browser"


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
            return response.json()["data"]["repository"]["projectV2"]["items"]["nodes"]
        else:
            raise Exception(
                f"GitHub API error: {response.status_code} - {response.text}"
            )

    def parse_roadmap_json(self, issue_body: str) -> Optional[Dict]:
        print(issue_body)
        """Issue説明からRoadmapのJSONを抽出"""
        # ### Roadmapの後に続くJSONを探す
        patterns = [
            # コードブロック内のJSONパターン
            r"### Roadmap\s*\n```json\s*\n({[^}]+})\s*\n```",
            # 直接JSONが書かれているパターン
            r"### Roadmap\s*\n({[^}]+})",
            # 改行があるJSONパターン
            r"### Roadmap\s*\n({[\s\S]*?})",
            # より柔軟なパターン（Baseline_Start_DateとBaseline_End_Dateを含む）
            r"### Roadmap[\s\S]*?({[\s\S]*?\"Baseline_Start_Date\"[\s\S]*?\"Baseline_End_Date\"[\s\S]*?})",
        ]

        for pattern in patterns:
            match = re.search(pattern, issue_body, re.MULTILINE | re.DOTALL)
            if match:
                json_str = match.group(1)
                # 余分な改行や空白を整理
                json_str = re.sub(r"\s+", " ", json_str)
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
        start_date = None
        end_date = None

        for field_value in item.get("fieldValues", {}).get("nodes", []):
            field_name = field_value.get("field", {}).get("name", "")
            if field_name.lower() in ["start date", "start"]:
                start_date = field_value.get("date")
            elif field_name.lower() in ["end date", "end", "due date", "due"]:
                end_date = field_value.get("date")

        return start_date, end_date

    def create_gantt_data(
        self, owner: str, repo: str, project_number: int
    ) -> pd.DataFrame:
        """GitHubプロジェクトからガントチャート用のデータを作成"""
        items = self.get_project_items(owner, repo, project_number)
        data = []

        for item in items:
            content = item.get("content")
            if not content:
                continue

            issue_title = content.get("title", "")
            issue_body = content.get("body", "")
            issue_number = content.get("number")

            # issue_numberが存在しない場合はスキップ
            if not issue_number:
                continue

            # 安全な文字列結合
            issue_label = f"#{str(issue_number)}: {issue_title}"

            # Actualデータ（プロジェクトから）
            actual_start, actual_end = self.extract_dates_from_project_item(item)

            if actual_start and actual_end:
                data.append(
                    {
                        "issue": issue_label,
                        "type": "Actual",
                        "start": actual_start,
                        "end": actual_end,
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
                        }
                    )

        df = pd.DataFrame(data)
        if not df.empty:
            df["start"] = pd.to_datetime(df["start"])
            df["end"] = pd.to_datetime(df["end"])

        return df

    def create_gantt_chart(self, df: pd.DataFrame) -> None:
        """二重線ガントチャートを作成"""
        if df.empty:
            print("データが見つかりませんでした")
            return

        # typeカテゴリの順序を指定してActualを上に表示
        df["type"] = pd.Categorical(
            df["type"], categories=["Actual", "Baseline"], ordered=True
        )

        fig = px.timeline(
            df,
            x_start="start",
            x_end="end",
            y="issue",
            color="type",
            color_discrete_map={"Baseline": "lightgray", "Actual": "steelblue"},
            category_orders={"type": ["Baseline", "Actual"]},
        )

        fig.update_layout(
            barmode="group",
            bargap=0.2,
            bargroupgap=0.1,
            title="GitHub Project Gantt Chart (Baseline vs Actual)",
            height=max(len(df["issue"].unique()) * 80, 400),
            yaxis=dict(
                categoryorder="category ascending",
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
                                count=7, label="1週間", step="day", stepmode="backward"
                            ),
                            dict(
                                count=14, label="2週間", step="day", stepmode="backward"
                            ),
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
                    y=i - 0.5, line_width=1, line_color="lightgray", opacity=0.5
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
            text=today,
            showarrow=False,
            font=dict(color="red"),
        )

        fig.show()


def main():
    # GitHub Personal Access Tokenをホームディレクトリから取得
    path = Path("~/.github/token.json").expanduser()
    token = None

    # ファイルを読み込み
    with path.open(encoding="utf-8") as f:
        token = json.load(f)["token"]
    if not token:
        print("~/.github/config.jsonを確認してください")
        return

    # 使用例
    owner = "tfukuda675"  # GitHubユーザー名
    repo = "my_todo"  # リポジトリ名
    project_number = 4  # プロジェクト番号

    try:
        chart = GitHubGanttChart(token)
        df = chart.create_gantt_data(owner, repo, project_number)
        chart.create_gantt_chart(df)
    except Exception as e:
        import traceback

        print(f"エラーが発生しました: {e}")
        print("詳細なトレースバック:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
