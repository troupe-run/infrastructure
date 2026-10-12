# Design

## Context

- **How the Claude Code rules work** (`scripts/guard.py`):
  - The `PreToolUse` hook (`.claude/settings.json`, matcher `Bash|PowerShell`) passes the command to
    `shell_decisions`.
  - `shell_decisions` splits the command into simple commands (`split_command`, heredoc bodies dropped). Each simple
    command goes through one function per rule (`guard_tamper`, `skip_hooks`, `pr_closes_issue`), each returning a
    `Decision`.
  - A refusal is denied unless the owner has granted a one-use override (`first_refusal`).
  - Rule ids live in `OVERRIDABLE_RULES`. `test_guard_docs.py` requires `docs/development-workflow.md` to list
    exactly those rules.
- **`pr_closes_issue` is the model for reading `gh`:** it knows which flags take a value, reads files the command
  names, and refuses what it can't check (stdin, a file that doesn't exist yet), with a fix.
- **The owner's login:** an OAuth token with `admin:org`, `repo` and `workflow`. Agents run `gh` with it.
  - `required-checks` showed that the owner's `pull_request` bypass merges past a failing required check (D8).
  - `prevent_self_review = false` on the CI environments.
- **Labels, repository settings, rulesets and environments are declared in OpenTofu here.** A change made by hand
  shows as drift and is reverted by the next apply.
- **The org holds 18 archived `bakeoff-*` and `spike-*` repositories,** kept as records (#1, Out of scope).
- **The guard is delivered to troupe.** `scripts/guard.py` changes there only through a plan the owner approves.

## Goals / Non-Goals

**Goals:**
- An agent can run, through `gh`, only what agents need. Everything else is refused with a fix.
- The acts reserved for the owner are refused with their own message, so a refusal says why, not just "not listed".
- Throwaway repositories stay usable for probes and spikes without an override.

**Non-Goals:**
- Stopping a determined bypass outside `gh`: `curl`, a script, an MCP tool. The hooks stop honest shortcuts
  (development-workflow, Known gaps).
- Checking anything online. The guard works offline, so whether a repository is archived isn't looked up.

## Decisions

### D1. Two rules: `owner-only` and `gh-allow-list`

**The owner chose an allow-list over a deny-list (2026-10-12).** A command nobody anticipated is refused, not
allowed. The refusals split two ways:

- **`owner-only`** covers the acts that are the owner's, named in D3. Its fix says to ask the owner, or to change the
  thing in troupe-run/infrastructure when OpenTofu manages it.
- **`gh-allow-list`** covers everything else not on the list. Its fix: "This gh command isn't on the guard's
  allow-list. Ask the owner, or add it to the list in troupe-run/infrastructure (scripts/guard.py)."

**`owner-only` is checked first.** A command that is both unlisted and reserved is refused as `owner-only`.

**Two ids, because an override is per rule.** The owner granting a `gh-allow-list` override for a harmless new
command shouldn't read, in the log, like letting an agent approve a deployment.

Both rules are overridable, like every rule except `guard-tamper`.

**Alternative: the deny-list first proposed** (refusing the named gates only). The owner turned it down: it misses
whatever nobody listed.

### D2. In any repository, with throwaway prefixes in `troupe-run`

The rules apply whatever repository a command names. The owner's rights span the org, and the habit would carry
anywhere.

**Throwaway repositories** are `troupe-run/infra-probe-*`, `troupe-run/spike-*` and `troupe-run/bakeoff-*`:
- agents may create one;
- agents may run any `gh` command against one, `gh api` writes included (rulesets, contents, refs);
- only `infra-probe-*` may be deleted by an agent;
- deleting, archiving or unarchiving `spike-*` or `bakeoff-*` is `owner-only` (owner, 2026-10-12). It works offline,
  and the archived records can't be lost.

**How the repository is found:**
- `-R`/`--repo`, or `GH_REPO` set for the command, as `pr_closes_issue` reads them;
- for `gh api`, the `repos/<owner>/<name>/` in the endpoint;
- for `gh repo create/delete/archive/unarchive`, the positional name.

A command whose repository can't be read isn't treated as a throwaway.

### D3. The table

The list is one constant in `scripts/guard.py`, grouped as below. In `gh api` paths, `<o>/<r>` matches any segment,
including gh's `{owner}`/`{repo}` placeholders and shell variables.

**Reads: allowed.**
- `pr view/list/checks/diff/status`;
- `issue view/list/status`;
- `run list/view/watch/download`;
- `repo view/list/clone`;
- `label list`;
- `project view/list/item-list/field-list`;
- `search <anything>`;
- `workflow list/view`;
- `release list/view`;
- `secret list`, `variable list`;
- `ruleset list/view/check`;
- `auth status`, without `-t`/`--show-token`;
- `gh --version`, `gh help`;
- `gh api` with `GET` or `HEAD`, on any endpoint;
- `gh api graphql` whose query has no `mutation`.

**Workflow writes: allowed.**
- `pr create/edit/ready/close/reopen/comment/checkout`;
- `pr merge` without `--admin`;
- `issue create/comment/edit/close/reopen`;
- `project item-add/item-edit/item-archive`;
- `workflow run`, `run rerun/cancel`;
- `gh api` writes:
  - `POST repos/<o>/<r>/issues/<n>/comments`, `.../issues/<n>/labels`, `.../issues/<n>/sub_issues`, and `DELETE` of
    one sub-issue;
  - `PATCH repos/<o>/<r>/issues/<n>`;
  - `POST repos/<o>/<r>/pulls/<n>/comments`, `.../pulls/<n>/reviews`;
- GraphQL mutations `updateIssue`, `addSubIssue`, `removeSubIssue`, `addComment`, `addProjectV2ItemById` and
  `updateProjectV2ItemFieldValue`.

**Throwaway repositories:** D2.

**`owner-only`, with its message group:**

- **Merge:** `pr merge --admin` (or `--admin=true`); any `gh api` write to `repos/<o>/<r>/pulls/<n>/merge`; GraphQL
  `mergePullRequest`.
- **Deployment:** a write to `repos/<o>/<r>/actions/runs/<id>/pending_deployments`; GraphQL `approveDeployments`,
  `rejectDeployments`.
- **Gates:** writes to rulesets (repository and org), `branches/<b>/protection…` and `environments/…`; GraphQL
  `*RepositoryRuleset`, `*BranchProtectionRule`.
- **Administration:**
  - `secret set/delete`, `variable set/delete`;
  - `repo create` (other than a throwaway), and `repo edit/rename/archive/unarchive/delete` (other than D2's
    exceptions);
  - `repo transfer`, `issue transfer/delete`;
  - `label create/edit/delete/clone`;
  - `project create/delete/edit/close/copy/link/unlink/mark-template/field-create/field-delete`;
  - GraphQL `updateProjectV2Field`;
  - a `gh api` write to:
    - `repos/<o>/<r>` itself;
    - `.../pages…`, `.../labels…`, `.../collaborators…`, `.../private-vulnerability-reporting`, `.../hooks…`;
    - `orgs/<o>`, `orgs/<o>/issue-types…`, `orgs/<o>/members…`, `orgs/<o>/teams…`;
    - any `.../secrets…` or `.../variables…`.
- **Credentials:** `auth token/login/logout/refresh/switch/setup-git`, and `auth status -t`/`--show-token`.

**`gh-allow-list`: everything else.** That includes `extension`, `alias`, any subcommand an alias or extension
defines, `config set`, `gpg-key`/`ssh-key` writes, and `gh api` writes to any other endpoint.

**How `gh` is read:**
- **The method:** `-X`/`--method` if given. Otherwise `POST` when any of `-f`, `-F`, `--raw-field`, `--field` or
  `--input` is given, and `GET` if not. That is gh's own rule, and a read with fields needs `-X GET`.
- **The endpoint:** a leading `https://api.github.com/` or `/` is dropped, along with any query string, and the
  result is lower-cased.
- **A GraphQL query** is read from `query=…` (`-f`/`-F`), from `query=@file`, or from `--input <file>`. A query from
  stdin (`@-`, `--input -`), or from a file that doesn't exist when the command starts, is refused by
  `gh-allow-list`, with a fix saying how to make it checkable. A query naming several mutations is allowed only if
  all of them are on the list.

### D4. The evidence: a survey of what agents ran

All of the Claude Code transcripts under `~/.claude-troupe/projects/` were read on 2026-10-12: 13 sessions across
troupe, infrastructure and its probes, with about 3,900 shell commands. The `gh` commands, grouped as in D3:

| Group | What was run (count) |
|---|---|
| Reads | `run list/view/watch` 194, `pr view/checks/list` 123, `issue view/list` 107, `repo view/list` 54, `gh api` `GET` about 250, GraphQL queries 17 |
| Workflow writes | `pr create/edit/ready/close` 52, `issue create/comment/edit/close/reopen` 64, `pr merge` 34 (none with `--admin`), `project item-add/item-edit` 17, GraphQL `updateIssue`/`addSubIssue` 13, `sub_issues` `POST` 3, `workflow run` 4 |
| Throwaway setup | `repo create/delete` 28, `contents` and `git/refs` writes, rulesets `POST`/`DELETE`, `createCommitOnBranch`: all on probes |
| Now `owner-only` | `label create` 4, `secret set` 5, `repo edit/rename` 7, `PUT pages` 6, issue types `POST` 2, `project create/link/field-create/delete` 7, GraphQL `updateProjectV2Field` 2, `issue transfer/delete` 3, `private-vulnerability-reporting` 1, `auth token` 5 |

Every allowed row came from this survey. Nothing on the list is speculative except the obvious neighbours of a
surveyed command (`issue reopen` next to `issue close`, `pr reopen`).

The counts are approximate. A few matches were prose mentioning `gh`, and the probe sessions inflate the setup rows.

### D5. The messages

- **Merge:** "only the owner merges past a pull request's rules." Fix: "Ask the owner to merge it, or fix what
  blocks it."
- **Deployment:** "only the owner approves or rejects a deployment." Fix: "Tell the owner the run is waiting, with
  its link."
- **Gates and administration:** "only the owner changes <what>." Fix: "Change it in troupe-run/infrastructure
  through a pull request, or ask the owner."
- **Credentials:** "agents don't handle the login's credentials." Fix: "Use gh itself; if something needs the token,
  ask the owner."
- **`gh-allow-list`:** D1.

### D6. Known gaps, documented in the rules doc

- **Any other HTTP client** with the owner's token. Refusing `gh auth token` narrows this, but a token can still be
  read from the keychain or a config file.
- **MCP tools.** The hook's matcher is `Bash|PowerShell` and the edit tools.
- **A command assembled at run time** (`eval`, `sh -c "$X"`), whose words aren't known before it runs.
- **A throwaway name is a convention.** An agent could create `troupe-run/spike-x` and do anything there. That's
  confined to a repository nothing depends on.

## Risks / Trade-offs

- **[A legitimate new command is refused]** → That's the price of failing closed. The fix says to ask the owner for
  a one-use override, or to add the command to the list by pull request here. The survey shows the list covers
  what agents have actually done.
- **[An agent needs to do an owner-only act while the owner is away]** → It waits. The gates exist so that it does.
- **[A read sent as `POST` because it has fields]** → It needs `-X GET`, and the fix text says so. The tests cover
  `-X GET` with fields.
- **[troupe's agents are restricted too]** → Intended: the owner's login is the same there. The delivery goes
  through the usual plan, and troupe's sessions see the same messages.
- **[The table drifts from what's documented]** → The docs name the rules and point to the table, not a copy of it.
  `test_guard_docs.py` keeps the rule ids in step.

## Migration Plan

1. On the branch: both rules, the table, their tests on all three OSes (CI), and the docs.
2. Open the pull request. Its plan shows `scripts/guard.py` delivered to troupe, and nothing else.
3. After the merge, the owner approves the apply. Check troupe's `guard` and CI on the delivery commit.

**Rollback:** revert through a pull request, and the next delivery restores the previous `guard.py` in troupe. A
person can grant a local override at any time.
