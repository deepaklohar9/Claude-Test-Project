# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This is a small, informal collection of standalone scripts — not a structured project. There is no package manifest, build tool, or dependency file (no `requirements.txt`, `pom.xml`, etc.); each file is self-contained and run directly.

Files:
- `Factorial.java` — computes factorial of 8 via a simple loop.
- `factorial.py` / `test_factorial.py` — Python factorial implementation with `unittest` coverage (0, 1, 5, 8).
- `jira_github_sync.py` — polls a Jira Cloud project for open issues and creates a matching GitHub issue for each one via the `gh` CLI, then comments back on the Jira issue with the GitHub link so it isn't re-synced on subsequent runs (idempotency check via a `"Synced to GitHub:"` marker in Jira comments).

## Environment

No JDK is on `PATH` by default in a fresh shell. If `javac`/`java` are not recognized, prepend the install path for the session:
```powershell
$env:Path = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot\bin;$env:Path"
```
The `gh` CLI must be authenticated (`gh auth status`) before `jira_github_sync.py` can create GitHub issues.

## Common commands

Compile and run the Java program:
```bash
javac Factorial.java && java Factorial
```

Run the Python factorial program:
```bash
python factorial.py
```

Run tests:
```bash
python -m unittest test_factorial -v
```

Run a single test:
```bash
python -m unittest test_factorial.TestFactorial.test_factorial_8
```

Run the Jira-GitHub sync script — requires these environment variables (`JIRA_API_TOKEN` must be a **classic/unscoped** Jira API token, generated at https://id.atlassian.com/manage-profile/security/api-tokens — scoped tokens have been observed to fail auth against `/rest/api/3/*`):
```bash
JIRA_SITE=<site>.atlassian.net JIRA_EMAIL=<account-email> JIRA_API_TOKEN=<token> \
JIRA_PROJECT_KEY=<key> GITHUB_REPO=<owner>/<repo> python jira_github_sync.py
```

## Architecture notes for jira_github_sync.py

- Jira access uses the REST API directly (`requests`, HTTP Basic Auth with email + API token) against the site's own domain, e.g. `https://<site>.atlassian.net/rest/api/3/...` — this is separate from and does not reuse any OAuth-based Jira MCP connector session.
- GitHub access shells out to the `gh` CLI (`gh issue create`) rather than calling GitHub's REST API directly, relying on `gh`'s own stored auth.
- Sync state is tracked entirely in Jira comments (no external database) — a comment containing `Synced to GitHub:` on an issue marks it as already processed, checked via `is_already_synced()`.
