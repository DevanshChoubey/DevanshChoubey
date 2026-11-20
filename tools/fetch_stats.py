"""Fetch live profile numbers into data/stats.json.

    GITHUB_TOKEN=... python3 tools/fetch_stats.py

Uses PROFILE_STATS_TOKEN when set (a read-only token of the profile owner, so
private contributions are counted), else GITHUB_TOKEN. The file only changes
when a number changes, so the daily workflow commits only on real updates.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

USER = "DevanshChoubey"
RELEASE_REPOS = ["shelllint", "radolint"]
OUT = Path(__file__).resolve().parent.parent / "data" / "stats.json"
API = "https://api.github.com"


def token():
    return os.environ.get("PROFILE_STATS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def request(url, payload=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
    if token():
        headers["Authorization"] = f"Bearer {token()}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    user = request(f"{API}/users/{USER}")
    repos = request(f"{API}/users/{USER}/repos?per_page=100&type=owner")
    stars = sum(r["stargazers_count"] for r in repos if not r["fork"])

    contributions = None
    if token():  # GraphQL needs auth
        q = {"query": "query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{totalContributions}}}}",
             "variables": {"u": USER}}
        res = request(f"{API}/graphql", q)
        contributions = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    releases = {}
    for name in RELEASE_REPOS:
        try:
            releases[name] = request(f"{API}/repos/{USER}/{name}/releases/latest")["tag_name"]
        except Exception:  # no release yet, or API hiccup: leave it out
            pass

    stats = {
        "public_repos": user["public_repos"],
        "stars": stars,
        "contributions": contributions,
        "releases": releases,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    json.dump(stats, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
