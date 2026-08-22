"""
Polls a Jira project for issues that haven't been synced to GitHub yet,
creates a matching GitHub issue for each, and comments back on the Jira
issue with a link so it isn't synced twice.

Requires environment variables:
    JIRA_SITE       e.g. "deepakai7171.atlassian.net"
    JIRA_EMAIL      the Atlassian account email
    JIRA_API_TOKEN  a token from https://id.atlassian.com/manage-profile/security/api-tokens
    JIRA_PROJECT_KEY  e.g. "TPJ"
    GITHUB_REPO     "owner/repo", e.g. "deepaklohar9/Claude-Test-Project"

Uses the `gh` CLI (already authenticated) for GitHub, and Jira's REST API
directly for Jira. Safe to re-run: issues already synced are skipped.
"""

import os
import subprocess
import sys

import requests

SYNC_MARKER = "Synced to GitHub:"


def get_env(name):
    value = os.environ.get(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def jira_session():
    email = get_env("JIRA_EMAIL")
    token = get_env("JIRA_API_TOKEN")
    session = requests.Session()
    session.auth = (email, token)
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    return session


def fetch_open_issues(session, site, project_key):
    url = f"https://{site}/rest/api/3/search/jql"
    params = {
        "jql": f'project = "{project_key}" AND statusCategory != Done ORDER BY created ASC',
        "fields": "summary,comment",
        "maxResults": 50,
    }
    resp = session.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get("issues", [])


def is_already_synced(issue):
    comments = issue.get("fields", {}).get("comment", {}).get("comments", [])
    for c in comments:
        body = c.get("body", "")
        text = body if isinstance(body, str) else str(body)
        if SYNC_MARKER in text:
            return True
    return False


def create_github_issue(repo, title, body):
    result = subprocess.run(
        ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def add_jira_comment(session, site, issue_key, comment_text):
    url = f"https://{site}/rest/api/3/issue/{issue_key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment_text}]}
            ],
        }
    }
    resp = session.post(url, json=payload)
    resp.raise_for_status()


def main():
    site = get_env("JIRA_SITE")
    project_key = get_env("JIRA_PROJECT_KEY")
    repo = get_env("GITHUB_REPO")

    session = jira_session()
    issues = fetch_open_issues(session, site, project_key)

    if not issues:
        print("No open Jira issues found.")
        return

    for issue in issues:
        key = issue["key"]
        summary = issue["fields"]["summary"]

        if is_already_synced(issue):
            print(f"[skip] {key} already synced")
            continue

        jira_url = f"https://{site}/browse/{key}"
        gh_url = create_github_issue(
            repo,
            title=f"[{key}] {summary}",
            body=f"Synced from Jira issue {key}: {jira_url}",
        )
        print(f"[sync] {key} -> {gh_url}")

        add_jira_comment(session, site, key, f"{SYNC_MARKER} {gh_url}")


if __name__ == "__main__":
    main()
