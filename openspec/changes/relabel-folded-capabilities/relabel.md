# Relabel record

Read from GitHub on 2026-10-26 before any edit (tasks 1.1-1.2): 120 troupe-run/troupe issues and 47 pull requests,
open and closed. 43 issues carry a folded label (14 open, 29 closed) and no pull request does. `cap:lifecycle` is on
nothing. 59 removals, and 43 additions on 36 issues. Every label to add is declared in `tofu/labels/troupe.json` and
exists on troupe-run/troupe. This matches design.md's tables.

## Mapping, read from each spec's `Capability:` line on troupe's `main`

| Folded label | Spec names |
|---|---|
| `cap:claude-code-runner` | `cap:actor-runners` |
| `cap:scripted-runner` | `cap:actor-runners` |
| `cap:runner-protocol` | `cap:actor-runners`, `cap:protocol` |
| `cap:run-workspaces` | `cap:stages`, `cap:vcs` |
| `cap:config-files` | `cap:config`, `cap:projections` |
| `cap:artifact-store` | `cap:storage` |
| `cap:client-protocol` | `cap:core-api`, `cap:protocol` |
| `cap:flake-hunt` | `cap:development` |
| `cap:python-support` | `cap:development` |
| `cap:quality-check` | `cap:development` |
| `cap:releases` | `cap:development` |
| `cap:docs-publishing` | `cap:development`, `cap:user-docs` |

## Each issue, before the edits

To put an issue back, set its labels to "Before".

| Issue | State | Before | Add | Remove |
|---|---|---|---|---|
| #4 | closed | `cap:actor-runners`, `cap:artifact-store`, `cap:event-store`, `cap:lineage`, `cap:runs` | `cap:storage` | `cap:artifact-store` |
| #5 | closed | `cap:config`, `cap:config-files`, `cap:event-store`, `cap:house`, `cap:platform` | `cap:projections` | `cap:config-files` |
| #6 | closed | `cap:config`, `cap:config-files`, `cap:theatre` | `cap:projections` | `cap:config-files` |
| #14 | closed | `cap:client-protocol`, `cap:core-api`, `cap:house`, `cap:identity`, `cap:platform`, `cap:projections`, `cap:protocol`, `cap:vcs` | none | `cap:client-protocol` |
| #16 | closed | `cap:actor-runners`, `cap:runner-protocol`, `cap:scripted-runner` | `cap:protocol` | `cap:runner-protocol`, `cap:scripted-runner` |
| #23 | closed | `cap:infrastructure`, `cap:releases` | `cap:development` | `cap:releases` |
| #33 | closed | `cap:actor-runners`, `cap:artifact-store`, `cap:cli`, `cap:client-protocol`, `cap:core-api`, `cap:event-store`, `cap:lineage`, `cap:projections`, `cap:protocol`, `cap:runner-protocol`, `cap:runs`, `cap:scripted-runner`, `cap:stages` | `cap:storage` | `cap:artifact-store`, `cap:client-protocol`, `cap:runner-protocol`, `cap:scripted-runner` |
| #34 | closed | `cap:actor-runners`, `cap:artifact-store`, `cap:lineage`, `cap:platform`, `cap:plugins`, `cap:protocol`, `cap:runner-protocol`, `cap:scripted-runner` | `cap:storage` | `cap:artifact-store`, `cap:runner-protocol`, `cap:scripted-runner` |
| #36 | closed | `cap:actor-runners`, `cap:cli`, `cap:client-protocol`, `cap:core-api`, `cap:effects`, `cap:event-store`, `cap:identity`, `cap:lineage`, `cap:performance`, `cap:platform`, `cap:policy`, `cap:projections`, `cap:protocol`, `cap:runs`, `cap:stages`, `cap:theatre` | none | `cap:client-protocol` |
| #51 | closed | `cap:artifact-store`, `cap:effects`, `cap:platform`, `cap:run-workspaces`, `cap:runs`, `cap:stages`, `cap:vcs` | `cap:storage` | `cap:artifact-store`, `cap:run-workspaces` |
| #55 | closed | `cap:actor-runners`, `cap:claude-code-runner`, `cap:runner-protocol` | `cap:protocol` | `cap:claude-code-runner`, `cap:runner-protocol` |
| #56 | open | `cap:actor-runners`, `cap:runner-protocol` | `cap:protocol` | `cap:runner-protocol` |
| #58 | open | `cap:plugins`, `cap:protocol`, `cap:scripted-runner` | `cap:actor-runners` | `cap:scripted-runner` |
| #60 | closed | `cap:actors`, `cap:config`, `cap:config-files`, `cap:policy`, `cap:protocol`, `cap:theatre` | `cap:projections` | `cap:config-files` |
| #64 | open | `cap:client-protocol`, `cap:core-api`, `cap:house`, `cap:identity`, `cap:protocol` | none | `cap:client-protocol` |
| #70 | closed | `cap:client-protocol`, `cap:event-store`, `cap:protocol`, `cap:runner-protocol` | `cap:actor-runners`, `cap:core-api` | `cap:client-protocol`, `cap:runner-protocol` |
| #73 | closed | `cap:cli`, `cap:client-protocol`, `cap:house`, `cap:platform` | `cap:core-api`, `cap:protocol` | `cap:client-protocol` |
| #76 | closed | `cap:cli`, `cap:client-protocol`, `cap:event-store`, `cap:lineage`, `cap:protocol`, `cap:runner-protocol`, `cap:runs`, `cap:scripted-runner` | `cap:actor-runners`, `cap:core-api` | `cap:client-protocol`, `cap:runner-protocol`, `cap:scripted-runner` |
| #83 | closed | `cap:quality-check`, `speed` | `cap:development` | `cap:quality-check` |
| #100 | closed | `cap:flake-hunt`, `cap:platform` | `cap:development` | `cap:flake-hunt` |
| #101 | closed | `cap:quality-check` | `cap:development` | `cap:quality-check` |
| #104 | closed | `cap:python-support`, `cap:releases` | `cap:development` | `cap:python-support`, `cap:releases` |
| #105 | closed | `cap:python-support`, `cap:releases` | `cap:development` | `cap:python-support`, `cap:releases` |
| #107 | closed | `cap:python-support`, `cap:releases` | `cap:development` | `cap:python-support`, `cap:releases` |
| #108 | closed | `cap:quality-check`, `speed` | `cap:development` | `cap:quality-check` |
| #109 | closed | `cap:quality-check`, `speed` | `cap:development` | `cap:quality-check` |
| #112 | closed | `cap:flake-hunt`, `cap:platform` | `cap:development` | `cap:flake-hunt` |
| #119 | open | `cap:config`, `cap:config-files`, `cap:lineage` | `cap:projections` | `cap:config-files` |
| #120 | closed | `cap:docs-publishing`, `cap:user-docs` | `cap:development` | `cap:docs-publishing` |
| #122 | open | `cap:client-protocol` | `cap:core-api`, `cap:protocol` | `cap:client-protocol` |
| #138 | open | `cap:config`, `cap:config-files` | `cap:projections` | `cap:config-files` |
| #139 | closed | `cap:releases` | `cap:development` | `cap:releases` |
| #140 | closed | `cap:protocol`, `cap:releases` | `cap:development` | `cap:releases` |
| #143 | open | `cap:releases` | `cap:development` | `cap:releases` |
| #144 | open | `cap:releases`, `cap:user-docs` | `cap:development` | `cap:releases` |
| #150 | open | `cap:platform`, `cap:run-workspaces`, `cap:runs`, `cap:stages`, `cap:vcs`, `needs:owner` | none | `cap:run-workspaces` |
| #151 | open | `cap:platform`, `cap:run-workspaces`, `cap:runs`, `cap:stages`, `cap:vcs` | none | `cap:run-workspaces` |
| #153 | open | `cap:run-workspaces`, `cap:runs`, `cap:stages`, `cap:vcs` | none | `cap:run-workspaces` |
| #154 | open | `cap:run-workspaces`, `cap:runs`, `cap:stages` | `cap:vcs` | `cap:run-workspaces` |
| #155 | closed | `cap:quality-check`, `cap:runner-protocol`, `cap:scripted-runner` | `cap:actor-runners`, `cap:development`, `cap:protocol` | `cap:quality-check`, `cap:runner-protocol`, `cap:scripted-runner` |
| #156 | open | `cap:config-files`, `cap:vcs` | `cap:config`, `cap:projections` | `cap:config-files` |
| #160 | closed | `cap:actor-runners`, `cap:claude-code-runner` | none | `cap:claude-code-runner` |
| #162 | open | `cap:actor-runners`, `cap:runner-protocol` | `cap:protocol` | `cap:runner-protocol` |

## Commands

Additions first (task 2.1):

```bash
gh issue edit 58 70 76 155 -R troupe-run/troupe --add-label cap:actor-runners
gh issue edit 156 -R troupe-run/troupe --add-label cap:config
gh issue edit 70 73 76 122 -R troupe-run/troupe --add-label cap:core-api
gh issue edit 23 83 100 101 104 105 107 108 109 112 120 139 140 143 144 155 -R troupe-run/troupe --add-label cap:development
gh issue edit 5 6 60 119 138 156 -R troupe-run/troupe --add-label cap:projections
gh issue edit 16 55 56 73 122 155 162 -R troupe-run/troupe --add-label cap:protocol
gh issue edit 4 33 34 51 -R troupe-run/troupe --add-label cap:storage
gh issue edit 154 -R troupe-run/troupe --add-label cap:vcs
```

Then removals (task 2.2):

```bash
gh issue edit 4 33 34 51 -R troupe-run/troupe --remove-label cap:artifact-store
gh issue edit 55 160 -R troupe-run/troupe --remove-label cap:claude-code-runner
gh issue edit 14 33 36 64 70 73 76 122 -R troupe-run/troupe --remove-label cap:client-protocol
gh issue edit 5 6 60 119 138 156 -R troupe-run/troupe --remove-label cap:config-files
gh issue edit 120 -R troupe-run/troupe --remove-label cap:docs-publishing
gh issue edit 100 112 -R troupe-run/troupe --remove-label cap:flake-hunt
gh issue edit 104 105 107 -R troupe-run/troupe --remove-label cap:python-support
gh issue edit 83 101 108 109 155 -R troupe-run/troupe --remove-label cap:quality-check
gh issue edit 23 104 105 107 139 140 143 144 -R troupe-run/troupe --remove-label cap:releases
gh issue edit 51 150 151 153 154 -R troupe-run/troupe --remove-label cap:run-workspaces
gh issue edit 16 33 34 55 56 70 76 155 162 -R troupe-run/troupe --remove-label cap:runner-protocol
gh issue edit 16 33 34 58 76 155 -R troupe-run/troupe --remove-label cap:scripted-runner
```

## Result

Run on 2026-10-26, additions then removals, as the commands above. After the additions, every issue carrying a folded
label carried every label its specs name (task 2.1). After the removals, `gh issue list` and `gh pr list` with
`--state all --label <l>` return nothing for each of the 13 labels, and all 43 issues' labels equal "Before" minus
"Remove" plus "Add", read back from GitHub (task 2.2).
