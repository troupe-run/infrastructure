# dependabot-issues fixtures

Payloads read from the real API on 2026-10-27 (dependabot-issues, task 3.1), for
`scripts/tests/test_dependabot_issues.py`. Each is trimmed only to the fields `scripts/dependabot_issues.py`
reads. Tests that need another value (a closed state, a missing closing line, another author) change that one
field of these files, so every shape is GitHub's own.

Pull requests, each read with
`gh api repos/troupe-run/<repo>/pulls/<n> --jq '{number,title,state,user:{login:.user.login,type:.user.type},head:{ref:.head.ref},body,merged_at,closed_at,html_url}'`:

| File | What it shows |
|---|---|
| `pull-website-44.json` | a patch update (zod 4.6.5 → 4.6.7), one of #172's test cases |
| `pull-website-55.json` | a major update (typescript 6.0.3 → 7.0.2) |
| `pull-website-58.json` | a scoped name (`@axe-core/playwright`), whose branch has a `/` inside the dependency |
| `pull-website-54.json` | a title from before the config, starting `build(deps):` |
| `pull-troupe-175.json` | `Update … requirement from <range> to <range>`: versions that aren't versions |
| `pull-infrastructure-184.json` | a `github-actions` update |

Others:

| File | Read with |
|---|---|
| `issue-website-21.json` | `gh api repos/troupe-run/website/issues/21 --jq '{number,title,state,state_reason,user:{login:.user.login,type:.user.type},body,labels:[.labels[].name],milestone:(.milestone\|if . then {number,title} else null end),closed_at,html_url}'`: an issue a bot opened, whose shape the App's issues share; tests change its author, labels and body |
| `milestones-website.json` | `gh api 'repos/troupe-run/website/milestones?state=open&per_page=100' --jq '[.[]\|{number,title,state}]'`: numbers that don't follow the version |
