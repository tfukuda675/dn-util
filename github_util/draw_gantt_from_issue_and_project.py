#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
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
        """Issue説明からRoadmapのJSONを抽出"""
        pattern = r"### Roadmap\s*\n```json\s*\n({[^}]+})\s*\n```"
        match = re.search(pattern, issue_body, re.MULTILINE | re.DOTALL)

        if not match:
            # 別のパターンも試す
            pattern = (
                r'### Roadmap.*?({.*?"Baseline_Start_Date".*?"Baseline_End_Date".*?})'
            )
            match = re.search(pattern, issue_body, re.MULTILINE | re.DOTALL)

        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
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

            # Actualデータ（プロジェクトから）
            actual_start, actual_end = self.extract_dates_from_project_item(item)

            if actual_start and actual_end:
                data.append(
                    {
                        "issue": f"#{issue_number}: {issue_title}",
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
                            "issue": f"#{issue_number}: {issue_title}",
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

        fig = px.timeline(
            df,
            x_start="start",
            x_end="end",
            y="issue",
            color="type",
            color_discrete_map={"Baseline": "lightgray", "Actual": "steelblue"},
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
            xaxis_title="日付",
            yaxis_title="Issue",
        )

        fig.update_traces(width=0.4)
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
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
