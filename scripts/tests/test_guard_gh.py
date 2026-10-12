"""The gh allow-list: owner-only acts and unlisted gh commands are refused in a Claude Code session
(spec: development-workflow; refuse-admin-merge design D1-D5)."""

import io
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import SCRIPTS, Repo, clean_env

import guard

GH_RULES = ("owner-only", "gh-allow-list")


def refusal(command: str, cwd: Path | None = None) -> guard.Decision | None:
    """The first refusal the gh rules give a command, or None if they allow it. Other rules, such
    as pr-closes-issue, are left to their own tests."""
    decisions = guard.shell_decisions(command, cwd or Path.cwd())
    return next((d for d in decisions if d.rule in GH_RULES), None)


def rule(command: str, cwd: Path | None = None) -> str | None:
    found = refusal(command, cwd)
    return found.rule if found else None


# Reads (D3)


@pytest.mark.parametrize(
    "command",
    [
        "gh pr view 17 -R troupe-run/infrastructure --json state",
        "gh pr list --state merged -L 1",
        "gh pr checks 17 --watch",
        "gh pr diff 17",
        "gh pr status",
        "gh issue view 1 --comments",
        "gh issue list --state all",
        "gh issue status",
        "gh run list --workflow tofu.yml",
        "gh run view 123 --log",
        "gh run watch 123",
        "gh run download 123 -n state-after-apply",
        "gh repo view troupe-run/troupe",
        "gh repo list troupe-run --limit 100",
        "gh repo clone troupe-run/troupe",
        "gh label list",
        "gh project view 1 --owner troupe-run",
        "gh project list --owner troupe-run",
        "gh project item-list 1 --owner troupe-run",
        "gh project field-list 1 --owner troupe-run",
        "gh search issues capability",
        "gh search code foo",
        "gh workflow list",
        "gh workflow view tofu.yml",
        "gh release list",
        "gh release view v1",
        "gh secret list --env apply",
        "gh variable list",
        "gh ruleset list",
        "gh ruleset view 1",
        "gh ruleset check main",
        "gh auth status",
        "gh --version",
        "gh help pr",
        "gh",
    ],
)
def test_each_listed_read_is_allowed(command: str) -> None:
    assert rule(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh api repos/troupe-run/troupe/rulesets",
        "gh api repos/troupe-run/infrastructure/environments --jq '.[]'",
        "gh api -X GET repos/troupe-run/troupe/pulls/31/merge",
        "gh api -X GET search/issues -f q=capability",
        "gh api --method HEAD repos/troupe-run/troupe",
        "gh api repos/troupe-run/infrastructure/actions/runs/1/pending_deployments",
        "gh api orgs/troupe-run/installations",
        'gh api graphql -f query=\'{ organization(login:"troupe-run") { projectV2(number:1) '
        "{ title } } }'",
        "gh api graphql -f query='query Q { viewer { login } }'",
    ],
)
def test_a_gh_api_read_is_allowed_on_any_endpoint(command: str) -> None:
    assert rule(command) is None


def test_a_graphql_query_whose_strings_mention_mutation_is_a_read() -> None:
    command = "gh api graphql -f query='{ search(query:\"mutation { mergePullRequest }\") { x } }'"
    assert rule(command) is None


# Workflow writes (D3)


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --title t --body 'Closes #16'",
        "gh pr edit 17 --title t",
        "gh pr ready 17",
        "gh pr close 17",
        "gh pr reopen 17",
        "gh pr comment 17 --body hi",
        "gh pr checkout 17",
        "gh pr merge 17 --rebase",
        "gh pr merge 17 --rebase --admin=false",
        "gh issue create --title t --body b",
        "gh issue comment 14 --body hi",
        "gh issue edit 1 --body-file b.md",
        "gh issue close 14",
        "gh issue reopen 14",
        "gh project item-add 1 --owner troupe-run --url https://github.com/x/y/issues/1",
        "gh project item-edit --id x --field-id y --project-id z --text t",
        "gh project item-archive 1 --owner troupe-run --id x",
        "gh workflow run tofu.yml --ref main",
        "gh run rerun 123",
        "gh run cancel 123",
    ],
)
def test_each_listed_workflow_write_is_allowed(command: str) -> None:
    assert rule(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh api repos/troupe-run/infrastructure/issues/14/comments -f body=hi",
        "gh api -X POST repos/troupe-run/troupe/issues/3/labels -f 'labels[]=bug'",
        "gh api -X DELETE repos/troupe-run/troupe/issues/3/labels/bug",
        "gh api repos/troupe-run/troupe/issues/3/sub_issues -F sub_issue_id=9",
        "gh api -X DELETE repos/troupe-run/troupe/issues/3/sub_issue -F sub_issue_id=9",
        "gh api -X PATCH repos/troupe-run/troupe/issues/3 -f state=closed",
        "gh api repos/troupe-run/troupe/pulls/3/comments -f body=hi",
        "gh api repos/troupe-run/troupe/pulls/3/reviews -f event=COMMENT",
    ],
)
def test_each_listed_api_write_is_allowed(command: str) -> None:
    assert rule(command) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "updateIssue",
        "addSubIssue",
        "removeSubIssue",
        "addComment",
        "addProjectV2ItemById",
        "updateProjectV2ItemFieldValue",
    ],
)
def test_each_listed_graphql_mutation_is_allowed(mutation: str) -> None:
    command = f"gh api graphql -f query='mutation {{ {mutation}(input:{{id:\"x\"}}) {{ a }} }}'"
    assert rule(command) is None


# owner-only (D3), with each message group (D5)


@pytest.mark.parametrize(
    ("command", "group"),
    [
        ("gh pr merge 17 --rebase --admin", "merge"),
        ("gh pr merge 17 --admin=true", "merge"),
        ("gh api -X PUT repos/troupe-run/troupe/pulls/31/merge", "merge"),
        ("gh api repos/troupe-run/troupe/pulls/31/merge -f merge_method=rebase", "merge"),
        ("gh api -X PUT https://api.github.com/repos/troupe-run/troupe/pulls/31/merge", "merge"),
        ("gh api -XPUT /repos/{owner}/{repo}/pulls/31/merge", "merge"),
        ("gh api -X PUT repos/$OWNER/$REPO/pulls/$PR/merge", "merge"),
        (
            "gh api repos/troupe-run/infrastructure/actions/runs/1/pending_deployments "
            "-F 'environment_ids[]=1' -f state=approved -f comment=ok",
            "deployment",
        ),
        ("gh api -X POST repos/troupe-run/troupe/rulesets --input r.json", "gates"),
        ("gh api -X PUT repos/troupe-run/troupe/rulesets/24895454 --input r.json", "gates"),
        ("gh api -X DELETE repos/troupe-run/troupe/rulesets/24895454", "gates"),
        ("gh api -X DELETE orgs/troupe-run/rulesets/1", "gates"),
        ("gh api -X PUT repos/troupe-run/troupe/branches/main/protection --input p.json", "gates"),
        ("gh api -X DELETE repos/troupe-run/troupe/branches/main/protection", "gates"),
        ("gh api -X PUT repos/troupe-run/infrastructure/environments/apply", "gates"),
        (
            "gh api -X POST repos/troupe-run/infrastructure/environments/apply/"
            "deployment-branch-policies -f name=x",
            "gates",
        ),
        ("gh secret set TF_VAR_x --env apply", "admin"),
        ("gh secret delete TF_VAR_x", "admin"),
        ("gh variable set X --body y", "admin"),
        ("gh variable delete X", "admin"),
        ("gh repo create troupe-run/new-thing --public", "admin"),
        ("gh repo create spike-x --public", "admin"),
        ("gh repo edit troupe-run/troupe --enable-wiki", "admin"),
        ("gh repo rename website -R troupe-run/troupe.run", "admin"),
        ("gh repo archive troupe-run/troupe --yes", "admin"),
        ("gh repo unarchive troupe-run/troupe --yes", "admin"),
        ("gh repo delete troupe-run/troupe --yes", "admin"),
        ("gh repo transfer x/y troupe-run", "admin"),
        ("gh issue transfer 1 troupe-run/troupe", "admin"),
        ("gh issue delete 1 --yes", "admin"),
        ("gh label create cap:x --color 000000", "admin"),
        ("gh label edit bug --color 000000", "admin"),
        ("gh label delete bug --yes", "admin"),
        ("gh label clone troupe-run/troupe", "admin"),
        ("gh project create --owner troupe-run --title x", "admin"),
        ("gh project delete 2 --owner troupe-run", "admin"),
        ("gh project edit 1 --owner troupe-run --title y", "admin"),
        ("gh project close 1 --owner troupe-run", "admin"),
        ("gh project copy 1 --source-owner troupe-run --target-owner x --title y", "admin"),
        ("gh project link 1 --owner troupe-run --repo troupe", "admin"),
        ("gh project unlink 1 --owner troupe-run --repo troupe", "admin"),
        ("gh project mark-template 1 --owner troupe-run", "admin"),
        ("gh project field-create 1 --owner troupe-run --name x --data-type TEXT", "admin"),
        ("gh project field-delete --id x", "admin"),
        ("gh api -X PATCH repos/troupe-run/infrastructure -F has_projects=true", "admin"),
        ("gh api -X DELETE repos/troupe-run/troupe", "admin"),
        ("gh api -X PUT repos/troupe-run/website/pages -f build_type=workflow", "admin"),
        ("gh api -X POST repos/troupe-run/troupe/labels -f name=x", "admin"),
        ("gh api -X PUT repos/troupe-run/troupe/collaborators/someone", "admin"),
        ("gh api -X PUT repos/troupe-run/troupe/private-vulnerability-reporting", "admin"),
        ("gh api -X POST repos/troupe-run/troupe/hooks -f name=web", "admin"),
        ("gh api -X PATCH orgs/troupe-run -f blog=x", "admin"),
        ("gh api -X POST orgs/troupe-run/issue-types -f name=Bug", "admin"),
        ("gh api -X PUT orgs/troupe-run/members/someone", "admin"),
        ("gh api -X POST orgs/troupe-run/teams -f name=x", "admin"),
        ("gh api -X PUT repos/troupe-run/troupe/actions/secrets/X -f encrypted_value=y", "admin"),
        ("gh api -X POST repos/troupe-run/troupe/actions/variables -f name=X", "admin"),
        ("gh auth token", "credentials"),
        ("gh auth login", "credentials"),
        ("gh auth logout", "credentials"),
        ("gh auth refresh -s admin:org", "credentials"),
        ("gh auth switch", "credentials"),
        ("gh auth setup-git", "credentials"),
        ("gh auth status --show-token", "credentials"),
        ("gh auth status -t", "credentials"),
    ],
)
def test_each_owner_only_act_is_refused_with_its_message(command: str, group: str) -> None:
    found = refusal(command)
    assert found is not None
    assert found.rule == "owner-only"
    assert (found.problem, found.fix) == guard.OWNER_ONLY_MESSAGES[group]


@pytest.mark.parametrize(
    ("mutation", "group"),
    [
        ("mergePullRequest", "merge"),
        ("approveDeployments", "deployment"),
        ("rejectDeployments", "deployment"),
        ("createRepositoryRuleset", "gates"),
        ("updateRepositoryRuleset", "gates"),
        ("deleteRepositoryRuleset", "gates"),
        ("createBranchProtectionRule", "gates"),
        ("updateBranchProtectionRule", "gates"),
        ("deleteBranchProtectionRule", "gates"),
        ("updateProjectV2Field", "admin"),
    ],
)
def test_each_owner_only_graphql_mutation_is_refused(mutation: str, group: str) -> None:
    command = (
        f"gh api graphql -f query='mutation M($id: ID!) {{ {mutation}(input:{{a:1}}) {{ b }} }}'"
    )
    found = refusal(command)
    assert found is not None
    assert found.rule == "owner-only"
    assert found.problem == guard.OWNER_ONLY_MESSAGES[group][0]


def test_an_aliased_owner_only_mutation_is_still_refused() -> None:
    command = "gh api graphql -f query='mutation { ok: mergePullRequest(input:{a:1}) { b } }'"
    assert rule(command) == "owner-only"


def test_a_mutation_read_from_a_query_file_is_checked(tmp_path: Path) -> None:
    (tmp_path / "q.graphql").write_text(
        'mutation {\n  mergePullRequest(input: {pullRequestId: "x"}) { clientMutationId }\n}\n',
        encoding="utf-8",
    )
    assert rule("gh api graphql -F query=@q.graphql", tmp_path) == "owner-only"


def test_a_mutation_read_from_an_input_file_is_checked(tmp_path: Path) -> None:
    body = {"query": "mutation { approveDeployments(input: {}) { deployments { id } } }"}
    (tmp_path / "body.json").write_text(json.dumps(body), encoding="utf-8")
    assert rule("gh api graphql --input body.json", tmp_path) == "owner-only"


def test_owner_only_applies_in_any_organisation() -> None:
    assert rule("gh pr merge 1 -R someone-else/thing --admin") == "owner-only"
    assert rule("gh api -X DELETE repos/someone-else/thing/rulesets/1") == "owner-only"


# gh-allow-list (D1, D3)


@pytest.mark.parametrize(
    "command",
    [
        "gh co 17",
        "gh my-extension do-something",
        "gh extension install owner/gh-thing",
        "gh alias set m 'pr merge --admin'",
        "gh config set editor vim",
        "gh gist create notes.md",
        "gh ssh-key add key.pub",
        "gh release create v1",
        "gh pr lock 17",
        "gh api -X PUT repos/troupe-run/troupe/contents/x.txt -f message=m -f content=eA==",
        "gh api -X POST repos/troupe-run/troupe/git/refs -f ref=refs/heads/x -f sha=abc",
        "gh api -X POST repos/troupe-run/troupe/statuses/abc -f state=success -f context=check",
        "gh api user/repos -f name=x",
    ],
)
def test_an_unlisted_gh_command_is_refused(command: str) -> None:
    found = refusal(command)
    assert found is not None
    assert found.rule == "gh-allow-list"
    assert "isn't on the guard's gh allow-list" in found.problem
    assert "-X GET" in found.fix


@pytest.mark.parametrize(
    "command",
    [
        "gh api graphql -F query=@-",
        "gh api graphql --input -",
        "gh api graphql -F query=@missing.graphql",
        "gh api graphql --input missing.json",
        "gh api graphql -f query='mutation { updateIssue(input:{a:1}) { b }'",
        "gh api graphql",
    ],
)
def test_a_graphql_query_that_can_t_be_read_first_is_refused_with_the_fix(command: str) -> None:
    found = refusal(command)
    assert found is not None
    assert found.rule == "gh-allow-list"
    assert "can't be checked" in found.problem
    assert "earlier command" in found.fix


def test_a_query_mixing_a_listed_and_an_unlisted_mutation_is_refused() -> None:
    command = (
        "gh api graphql -f query='mutation { updateIssue(input:{a:1}) { b } "
        "createCommitOnBranch(input:{a:1}) { c } }'"
    )
    assert rule(command) == "gh-allow-list"


def test_owner_only_is_checked_before_the_allow_list() -> None:
    command = (
        "gh api graphql -f query='mutation { createCommitOnBranch(input:{a:1}) { c } "
        "mergePullRequest(input:{a:1}) { b } }'"
    )
    assert rule(command) == "owner-only"


# Throwaway repositories (D2)


@pytest.mark.parametrize("name", ["infra-probe-20261013", "spike-x", "bakeoff-specs-y"])
@pytest.mark.parametrize(
    "template",
    [
        "gh repo create troupe-run/{name} --public",
        "gh api -X PUT repos/troupe-run/{name}/contents/x.txt -f message=m -f content=eA==",
        "gh api -X POST repos/troupe-run/{name}/rulesets --input r.json",
        "gh api -X POST repos/troupe-run/{name}/statuses/abc -f state=success",
        "gh pr merge 1 -R troupe-run/{name} --rebase --admin",
        "gh label create x -R troupe-run/{name}",
        "gh release create v1 -R troupe-run/{name}",
        "GH_REPO=troupe-run/{name} gh secret set X",
    ],
)
def test_anything_may_be_done_to_a_throwaway_repository(template: str, name: str) -> None:
    assert rule(template.format(name=name)) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh repo delete troupe-run/infra-probe-20261013 --yes",
        "gh api -X DELETE repos/troupe-run/infra-probe-20261013",
        "gh repo archive troupe-run/infra-probe-20261013 --yes",
    ],
)
def test_a_probe_repository_may_be_deleted(command: str) -> None:
    assert rule(command) is None


@pytest.mark.parametrize("name", ["spike-claude-docker", "bakeoff-specs"])
@pytest.mark.parametrize(
    "template",
    [
        "gh repo delete troupe-run/{name} --yes",
        "gh repo archive troupe-run/{name} --yes",
        "gh repo unarchive troupe-run/{name} --yes",
        "gh repo rename x -R troupe-run/{name}",
        "gh api -X DELETE repos/troupe-run/{name}",
        "gh api -X PATCH repos/troupe-run/{name} -F archived=false",
    ],
)
def test_a_spike_or_bake_off_record_can_t_be_deleted_or_unarchived(
    template: str, name: str
) -> None:
    assert rule(template.format(name=name)) == "owner-only"


@pytest.mark.parametrize(
    "command",
    [
        "gh repo delete someone-else/infra-probe-x --yes",
        "gh repo create infra-probe-x --public",
        "gh api -X POST repos/someone-else/spike-x/rulesets --input r.json",
        "gh repo delete troupe-run/troupe-infra-probe --yes",
    ],
)
def test_the_prefixes_count_only_in_troupe_run(command: str) -> None:
    assert rule(command) == "owner-only"


def test_an_extension_isn_t_exempt_on_a_throwaway_repository() -> None:
    assert rule("gh my-extension go -R troupe-run/infra-probe-x") == "gh-allow-list"


def test_credentials_aren_t_exempt_on_a_throwaway_repository() -> None:
    assert rule("GH_REPO=troupe-run/infra-probe-x gh auth token") == "owner-only"


# Mentions and chains


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'refuse gh pr merge --admin and gh auth token'",
        "git commit -q -F - <<'EOF'\nfix: refuse gh pr merge --admin\n\ngh auth token too\nEOF",
        "echo 'gh api graphql mergePullRequest'",
        "grep -n 'gh secret set' README.md",
    ],
)
def test_a_mention_isn_t_a_command(command: str) -> None:
    assert rule(command) is None


def test_a_refused_act_chained_after_an_allowed_one_is_refused() -> None:
    assert rule("gh pr view 1 && gh pr merge 1 --admin") == "owner-only"
    assert rule("gh run list; gh auth token | pbcopy") == "owner-only"


# The survey (D4): one example of each command shape agents ran in earlier sessions, written here
# rather than read from transcripts, classified as design D4's table says.

SURVEY: list[tuple[str, str | None]] = [
    ("gh run list -R troupe-run/infrastructure --workflow tofu.yml --branch main", None),
    ("gh run view 38221592710 -R troupe-run/infrastructure --json jobs", None),
    ("gh run watch 123", None),
    ("gh pr view 17 -R troupe-run/infrastructure --json comments", None),
    ("gh pr checks 17 -R troupe-run/infrastructure --watch --interval 10", None),
    ("gh pr list -R troupe-run/infrastructure --state merged -L 1", None),
    ("gh issue view 1 -R troupe-run/infrastructure --json body", None),
    ("gh issue list -R troupe-run/infrastructure --state all", None),
    ("gh repo view troupe-run/infra-probe-20261012", None),
    ("gh repo list troupe-run --limit 100 --json name,isArchived", None),
    ("gh api repos/troupe-run/troupe/commits/refs/pull/13/head/check-runs", None),
    ("gh api repos/troupe-run/infrastructure/rulesets", None),
    (
        'gh api graphql -f query=\'{ organization(login:"troupe-run") { projectV2(number:2) '
        "{ title } } }'",
        None,
    ),
    ("gh pr create -R troupe-run/infrastructure --title t --body-file pr.md", None),
    ("gh issue create -R troupe-run/infrastructure --title t --body-file b.md", None),
    ("gh issue comment 14 -R troupe-run/infrastructure --body-file c.md", None),
    ("gh issue edit 1 -R troupe-run/infrastructure --body-file issue1.md", None),
    ("gh pr merge 2 -R troupe-run/infra-probe-20261012 --rebase", None),
    ("gh project item-add 2 --owner troupe-run --url https://github.com/x/y/issues/4", None),
    ("gh api graphql -f query='mutation { updateIssue(input:{id:\"x\"}) { issue { id } } }'", None),
    ("gh api repos/troupe-run/troupe/issues/3/sub_issues -F sub_issue_id=9", None),
    ("gh workflow run tofu.yml -R troupe-run/infrastructure --ref main", None),
    ("gh repo create troupe-run/infra-probe-20261012 --public --add-readme", None),
    ("gh repo delete troupe-run/infra-probe-20261012 --yes", None),
    (
        "gh api -X POST repos/troupe-run/infra-probe-20261012/statuses/96aa494 -f state=success",
        None,
    ),
    ("gh api -X PATCH repos/troupe-run/infra-probe-20261012 -F has_projects=true", None),
    ("gh label create cap:x -R troupe-run/troupe --color 1D76DB", "owner-only"),
    ("gh secret set TF_VAR_github_app_pem --env apply -R troupe-run/infrastructure", "owner-only"),
    ("gh repo edit troupe-run/website --homepage https://troupe.run", "owner-only"),
    ("gh api -X PUT repos/troupe-run/website/pages -f cname=troupe.run", "owner-only"),
    ("gh api -X POST orgs/troupe-run/issue-types -f name=Decision", "owner-only"),
    ("gh project create --owner troupe-run --title x", "owner-only"),
    ("gh project link 2 --owner troupe-run --repo infra-probe-20261012", "owner-only"),
    (
        "gh api graphql -f query='mutation { updateProjectV2Field(input:{a:1}) { b } }'",
        "owner-only",
    ),
    ("gh issue transfer 3 troupe-run/troupe", "owner-only"),
    ("gh api -X PUT repos/troupe-run/troupe/private-vulnerability-reporting", "owner-only"),
    ("gh auth token", "owner-only"),
    ("gh pr merge 1 -R troupe-run/infrastructure --rebase --admin", "owner-only"),
]


@pytest.mark.parametrize(("command", "expected"), SURVEY)
def test_each_surveyed_command_is_classified_as_the_design_says(
    command: str, expected: str | None
) -> None:
    assert rule(command) == expected


# End to end, through the PreToolUse hook


def run_hook(repo: Repo, command: str) -> str:
    payload: dict[str, object] = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(repo.path),
    }
    out = io.StringIO()
    guard.run_claude_pre_tool_use(payload, stdout=out)
    return out.getvalue()


def grant(repo: Repo, rule_id: str) -> None:
    subprocess.run(
        [sys.executable, str(SCRIPTS / "guard.py"), "override", rule_id, "--reason", "owner says"],
        cwd=repo.path,
        capture_output=True,
        text=True,
        check=True,
        env=clean_env(),
    )


def test_the_hook_denies_an_admin_merge_naming_the_rule_and_fix(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    output = json.loads(run_hook(repo, "gh pr merge 17 --rebase --admin"))
    decision = output["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "guard: owner-only:" in decision["permissionDecisionReason"]
    assert "Ask the owner to merge it" in decision["permissionDecisionReason"]


def test_the_hook_allows_a_read(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    assert run_hook(repo, "gh pr view 17 --json state") == ""


def test_an_owner_only_override_lets_exactly_one_command_through(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    grant(repo, "owner-only")
    assert run_hook(repo, "gh pr merge 17 --rebase --admin") == ""
    assert "owner-only" in run_hook(repo, "gh pr merge 17 --rebase --admin")


def test_an_allow_list_override_doesn_t_unlock_an_owner_only_refusal(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    grant(repo, "gh-allow-list")
    assert "owner-only" in run_hook(repo, "gh auth token")
    assert run_hook(repo, "gh extension install owner/gh-thing") == ""
