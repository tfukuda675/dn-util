#! /Users/tfuku/Tools/miniforge3/envs/py313/bin/python3

import os, textwrap
import json
import sys
import requests
from github import Github

TOKEN = None
home_dir = os.path.expanduser("~")
with open(f"{home_dir}/.github/token.json") as f:
    TOKEN = json.load(f)["token"]

GITHUB_API_URL = "https://api.github.com/graphql"
OWNER            = "nsitexe"
PROJECT_NUMBER   = 94  # Project number (not ID)

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

query_org = """
query($owner: String!, $number: Int!, $after: String) {
  organization(login: $owner) {
    projectV2(number: $number) {
      title
      fields(first: 50) {
        nodes {
          ... on ProjectV2FieldCommon {
            id
            name
            dataType
          }
        }
      }
      items(first: 100, after: $after) {
        nodes {
          content {
            ... on Issue {
              title
              number
              url
              state
              createdAt
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
                date
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""

#  ________________________________________
#  _____/  [x] user用 query          \_____
#
query_user = """
query($owner: String!, $number: Int!) {
  user(login: $owner) {
    projectV2(number: $number) {
      id
      title
      fields(first: 20) {
        nodes {
          ... on ProjectV2Field {
            name
            dataType
          }
        }
      }
      items(first: 20) {
        nodes {
          content {
            ... on Issue {
              title
              number
              url
            }
          }
        }
      }
    }
  }
}
"""


def fetch_all_items():
    after_cursor  = None
    all_items     = []
    project_title = None

    while True:
        variables = {
            "owner":  OWNER,
            "number": PROJECT_NUMBER,
            "after":  after_cursor,
        }

        response = requests.post(
            GITHUB_API_URL,
            json={"query": query_org, "variables": variables},
            headers=headers,
        )
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            break

        data     = response.json()
        project  = data["data"]["organization"]["projectV2"]
        if not project_title:
            project_title = project["title"]

        items = project["items"]["nodes"]
        all_items.extend(items)

        page_info = project["items"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break

        after_cursor = page_info["endCursor"]

    return project_title, all_items



# フィールドから開始・完了日を抽出して表示
def display_items(project_title, items, ghobj):
    print(f"\n■ Project: {project_title} – {len(items)} items\n")

    for item in items:
        content = item.get("content")
        if not content:
            continue

        title      = content["title"]
        url        = content["url"]
        repo_name  = content["url"].split("/")[4]
        issue_no   = content["url"].split("/")[6]
        create_at  = content["createdAt"]
        assignees  = [node["login"] for node in content["assignees"]["nodes"]]

        start_date = None
        end_date   = None
        priority   = None
        status     = None
        size       = None

        for field_value in item["fieldValues"]["nodes"]:
            if field_value == {} or field_value.get("field") is None:
                continue

            field_name = field_value["field"]["name"]
            date       = field_value.get("date")

            # 日付情報
            if field_name in ["開始日", "Start Date", "Start date"]:
                start_date = date
            elif field_name in ["完了日", "Due Date", "End Date", "End date"]:
                end_date = date

            # プライオリティ
            if field_name in ["Priority"]:
                priority = field_value.get("name")

            # ステータス
            if field_name in ["Status"]:
                status = field_value.get("name")

            # サイズ
            if field_name in ["Size"]:
                size = field_value.get("name")


        print(f"- Title      : {title}")
        print(f"  URL        : {url}")
        print(f"  Assignees  : {', '.join(assignees)}")
        print(f"  作成日       : {create_at}")
        print(f"  開始日       : {start_date}")
        print(f"  完了日       : {end_date}")
        print(f"  プライオリティ: {priority}")
        print(f"  ステータス    : {status}")
        print(f"  サイズ       : {size}")
        print(f"  Repo       : {repo_name}")
        print(f"  Issue No   : {issue_no}\n")

        display_issue_items(repo_name, int(issue_no), ghobj)


# Issue からの情報を取得して表示
def display_issue_items(repo_name, issue_no, ghobj):
    # 1. GitHub API を使用してリポジトリ情報を取得
    repo  = ghobj.get_repo(f"{OWNER}/{repo_name}")
    issue = repo.get_issue(number=issue_no)

    # 2. コメント情報を取得
    comments = issue.get_comments()

    # 3. Issue 情報を表示
    print(f"Total comments found: {comments.totalCount}")
    print(" " * 4 + "-" * 40)
    for comment in comments:
        print(" " * 4 + f"Author    : {comment.user.login}")
        print(" " * 4 + f"Comment   : {comment.body}")
        print(" " * 4 + f"Created at: {comment.created_at}")
        print(" " * 4 + "-" * 40)
    print("")
    print("")


if __name__ == "__main__":
    gh = Github(TOKEN)
    project_title, all_items = fetch_all_items()
    display_items(project_title, all_items, gh)

