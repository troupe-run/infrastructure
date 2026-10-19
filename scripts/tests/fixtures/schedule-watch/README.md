# Schedule-watch fixtures

Payloads read from the real API on 2026-10-19 (watch-website-link-check, task 2.1), for
`scripts/tests/test_watch_schedules.py`. Each is trimmed only to the fields `scripts/watch_schedules.py`
reads. Tests that need another value (a disabled state, an older run) change that one field of these files,
so every shape is GitHub's own.

| File | Read with |
|---|---|
| `workflow.json` | `gh api repos/troupe-run/website/actions/workflows/links-weekly.yml --jq '{id,name,path,state,html_url}'` |
| `runs.json` | `gh api 'repos/troupe-run/website/actions/workflows/links-weekly.yml/runs?event=schedule&per_page=1' --jq '{total_count, workflow_runs: [.workflow_runs[] \| {id,event,status,conclusion,created_at,html_url}]}'` |
| `runs-empty.json` | `gh api 'repos/troupe-run/infrastructure/actions/workflows/ci.yml/runs?event=schedule&per_page=1'` (ci.yml has no schedule) |
| `not-found.json`, `not-found.stderr` | `gh api repos/troupe-run/website/actions/workflows/nope.yml`: its stdout and stderr; it exits 1 |
| `issues.json` | `gh issue list -R troupe-run/website --state all --limit 1000 --json number,title,author,createdAt,state,url`, issues 18, 19 and 21: two opened by the workflow's token, one by a person |
| `issue-view.json` | `gh issue view 21 -R troupe-run/website --json body,comments --jq '{body, comments: [.comments[] \| {author: {login: .author.login}, body, createdAt}]}'` |

`gh issue list` names the workflow's token `app/github-actions`; `gh issue view`'s comments name it
`github-actions`. The script reads each as its own command gives it.
