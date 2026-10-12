# Proposal

Issue: #16, a follow-up from `required-checks` (#14). The owner's decisions of 2026-10-12 are recorded in design.md
(D1–D3):
- the scope is every act only the owner should do, in any repository;
- agents' `gh` commands are allow-listed rather than deny-listed;
- org and repository admin goes through this repository;
- unknown commands are refused;
- throwaway repositories are open to agents, and only `infra-probe-*` may be deleted.

## Why

`required-checks` made a red pull request unmergeable, except through the owner's bypass, which is meant as a
break-glass. An agent in a Claude Code session works with the owner's `gh` login (`admin:org`, `repo`, `workflow`).
GitHub can't tell the two apart, so the agent can use the same bypass. The `--admin` merge is only the most visible
case. The same login can also:
- **approve the agent's own plan or apply** (`prevent_self_review = false`);
- **edit a ruleset or an environment**, change repository settings, or set secrets;
- **print the token itself** (`gh auth token`), for any other client to use.

A list of the known bad acts would miss the next one nobody thought of. A list of what agents actually need, built
from what they have run, fails closed instead.

## What Changes

Two new Claude Code rules apply to every `gh` command in a session, in any repository.

- **`owner-only`** refuses the acts reserved for the owner. Its fix names the owner, or this repository for anything
  OpenTofu manages:
  - merging past a pull request's rules: `gh pr merge --admin`, and any merge through the API;
  - approving or rejecting a deployment;
  - changing a ruleset, branch protection or an environment;
  - org and repository admin:
    - secrets and variables;
    - creating (other than a throwaway), editing, renaming, archiving, deleting or transferring a repository;
    - Pages and issue types;
    - project definitions;
    - labels, which OpenTofu owns;
    - moving or deleting issues;
  - credentials: `gh auth token`, `login`, `logout`, `refresh`.
- **`gh-allow-list`** refuses every other `gh` command that isn't on the allow-list. That includes an unknown
  subcommand, an extension, an alias, and a `gh api` write to an endpoint not on the list. The allow-list holds:
  - every read;
  - the everyday workflow writes: pull requests and issues, comments, sub-issues, project items, and running and
    re-running workflows;
  - anything on a throwaway repository in `troupe-run` (`infra-probe-*`, `spike-*`, `bakeoff-*`). Agents may create
    them and write to them, but only `infra-probe-*` may be deleted. Deleting, archiving or unarchiving a `spike-*`
    or `bakeoff-*` repository is owner-only, because 18 archived ones are kept as records.
- **Both rules can be overridden** by the owner, for one action, in their own terminal.
- **The list lives in one table in `scripts/guard.py`.** Its evidence is a survey of the `gh` commands agents ran in
  13 earlier sessions.
- **The rules doc gains both rules and their known gaps:** other HTTP clients, MCP tools, and commands assembled at
  run time. These hooks still aren't a security boundary.
- **The guard is delivered to troupe** through the usual plan.

Out of scope:
- refusing these acts on GitHub itself, which can't tell an agent from the owner when the token is the owner's;
- commands other than `gh`, such as `curl` or scripts. That gap is documented.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- **`development-workflow`:** two new requirements, "Agents don't act as the owner" and "Agents' gh commands are
  allow-listed", with their scenarios. The rules table and known gaps in `docs/development-workflow.md` follow.

## Impact

- **Changed:**
  - `scripts/guard.py`: both rules and the allow-list table, added to `OVERRIDABLE_RULES` and `shell_decisions`;
  - `scripts/tests/test_guard_gh.py` (new);
  - `docs/development-workflow.md`.
- **Delivered:** `scripts/guard.py` to troupe, by the App after the owner approves the plan.
- **Agents in both repositories:** some commands they ran before are now refused, with a fix. In the survey, those
  were label creation, secrets, repository edits, Pages and issue types. All of them belong in OpenTofu or with the
  owner.
- **The owner, by hand:** approves the plans and the apply, and grants overrides when an agent should do one of
  these.
