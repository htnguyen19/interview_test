"""Fetch merged pull requests from a GitHub repo and write them to a CSV.

Usage:
    python fetch_merged_prs.py owner/repo [-o merged_prs.csv]

Set GITHUB_TOKEN to raise the rate limit (60/hr unauthenticated) or read private repos.
Each merged PR costs one extra request (additions/deletions/merged_by are only on the detail endpoint).
"""
import argparse
import csv
import json
import os
import re
import urllib.request
from datetime import datetime

API = "https://api.github.com"
FIELDS = [
    "pr_number", "title", "url",
    "author_login", "author_id", "author_url", "author_type",
    "merged_by_login", "merged_by_id", "merged_by_url",
    "additions", "deletions",
    "created_at", "merged_at", "time_to_merge",
]


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        link = resp.headers.get("Link", "")
        next_url = re.search(r'<([^>]+)>;\s*rel="next"', link)
        return json.load(resp), next_url and next_url.group(1)


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def row(pr):
    author, merger = pr["user"] or {}, pr["merged_by"] or {}
    return {
        "pr_number": pr["number"],
        "title": pr["title"],
        "url": pr["html_url"],
        "author_login": author.get("login"),
        "author_id": author.get("id"),
        "author_url": author.get("html_url"),
        "author_type": author.get("type"),
        "merged_by_login": merger.get("login"),
        "merged_by_id": merger.get("id"),
        "merged_by_url": merger.get("html_url"),
        "additions": pr["additions"],
        "deletions": pr["deletions"],
        "created_at": pr["created_at"],
        "merged_at": pr["merged_at"],
        "time_to_merge": parse(pr["merged_at"]) - parse(pr["created_at"]),  # H:MM:SS, "N days, ..." if long
    }


def merged_prs(repo):
    url = f"{API}/repos/{repo}/pulls?state=closed&per_page=100"
    while url:
        page, url = get(url)
        for summary in page:
            if summary["merged_at"]:  # closed-without-merge PRs have merged_at = null
                detail, _ = get(summary["url"])
                yield row(detail)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", default="htnguyen19/interview_test", help="owner/repo")
    parser.add_argument("-o", "--output", default="merged_prs.csv")
    args = parser.parse_args()

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        count = 0
        for r in merged_prs(args.repo):
            writer.writerow(r)
            count += 1
    print(f"Wrote {count} merged PRs to {args.output}")


if __name__ == "__main__":
    main()
