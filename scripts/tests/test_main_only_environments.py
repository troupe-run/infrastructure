"""The environments only main may use stay declared that way (specs: ci-apply, release-credentials,
repositories, board-credentials, docs-build-credentials; check-main-only-environments design D1 to
D3).

prevent_destroy goes with its block: deleting an environment's declaration plans a destroy that
nothing refuses, and the next job that names the environment makes GitHub recreate it with no
branch rule and no reviewer (#61). So this test reads the declarations as text and fails when one
of these environments is no longer declared, no longer limited to main, or open to an admin bypass.
Removing one means changing MAIN_ONLY below, in the same diff the owner reviews. `board` and `docs`
are each in two repositories (watch-website-link-check design D5, rebuild-site-on-milestones design
D1), so an environment is named with its repository wherever its name alone would be ambiguous.
"""

import re
from dataclasses import dataclass, field

import pytest
from conftest import REPO

pytestmark = pytest.mark.tofu

TF_FILES = (
    REPO / "tofu" / "environments.tf",
    REPO / "tofu" / "release.tf",
    REPO / "tofu" / "board.tf",
    REPO / "tofu" / "docs.tf",
)


# The one place that says which environments are main-only (design D1), keyed by the module that
# declares the repository and the environment's name. The value is whether the owner must be a
# required reviewer. plan-main has no reviewer by design, so it isn't checked either way.
MAIN_ONLY = {
    ("repo_infrastructure", "plan-main"): False,
    ("repo_infrastructure", "apply"): True,
    ("repo_troupe", "release"): False,
    ("repo_website", "github-pages"): False,
    ("repo_website", "board"): False,
    ("repo_infrastructure", "board"): False,
    ("repo_troupe", "docs"): False,
    ("repo_infrastructure", "docs"): False,
}


UPDATE = "; update this test to read it"


@dataclass
class Block:
    """An HCL block: its type and labels, its attributes as whitespace-collapsed expression text,
    and its nested blocks."""

    type: str
    labels: tuple[str, ...] = ()
    attrs: dict[str, str] = field(default_factory=dict)
    blocks: list["Block"] = field(default_factory=list)


def strip_comments(text: str) -> str:
    """The text without `#`, `//` and `/* */` comments, leaving string literals alone."""
    out: list[str] = []
    i = 0
    in_string = False
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(text[i : i + 2] if char == "\\" else char)
            i += 2 if char == "\\" else 1
            in_string = char != '"'
        elif char == '"':
            in_string = True
            out.append(char)
            i += 1
        elif char == "#" or text.startswith("//", i):
            newline = text.find("\n", i)
            i = len(text) if newline < 0 else newline
        elif text.startswith("/*", i):
            i = text.index("*/", i) + 2
            out.append(" ")
        else:
            out.append(char)
            i += 1
    return "".join(out)


IDENTIFIER = re.compile(r"[A-Za-z_][\w-]*")
LABEL = re.compile(r'\s*"([^"]*)"')


def read_expression(text: str, i: int) -> tuple[str, int]:
    """An attribute's expression from i to the end of its line, across brackets and strings."""
    depth = 0
    in_string = False
    start = i
    while i < len(text):
        char = text[i]
        if in_string:
            i += 2 if char == "\\" else 1
            in_string = char != '"'
            continue
        if char == '"':
            in_string = True
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif char == "\n" and depth == 0:
            break
        i += 1
    return " ".join(text[start:i].split()), i


def parse_body(text: str, i: int, block: Block) -> int:
    """Fill block from text at i, up to its closing brace (or the end of the file)."""
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] == "}":
            return i + 1
        name = IDENTIFIER.match(text, i)
        if not name:
            raise ValueError(f"can't read the HCL at {text[i : i + 30]!r}{UPDATE}")
        i = name.end()
        while text[i] in " \t":
            i += 1
        if text[i] == "=" and text[i + 1] != "=":
            block.attrs[name.group()], i = read_expression(text, i + 1)
            continue
        labels = []
        while label := LABEL.match(text, i):
            labels.append(label.group(1))
            i = label.end()
        while text[i].isspace():
            i += 1
        if text[i] != "{":
            raise ValueError(f"can't read the block {name.group()!r}{UPDATE}")
        child = Block(name.group(), tuple(labels))
        block.blocks.append(child)
        i = parse_body(text, i + 1, child)


def parse(text: str) -> Block:
    root = Block("file")
    parse_body(strip_comments(text), 0, root)
    return root


@dataclass(frozen=True)
class Environment:
    name: str
    repository: str
    can_admins_bypass: bool
    branch_policy: Block | None
    reviewers: tuple[str, ...]


def literal_string(expression: str) -> str:
    match = re.fullmatch(r'"([^"$]*)"', expression)
    if not match:
        raise ValueError(f"{expression!r} isn't a string literal{UPDATE}")
    return match.group(1)


def boolean(expression: str, entry: dict[str, bool] | None) -> bool:
    if expression in ("true", "false"):
        return expression == "true"
    each = re.fullmatch(r"each\.value\.(\w+)", expression)
    if each and entry is not None and each.group(1) in entry:
        return entry[each.group(1)]
    raise ValueError(f"{expression!r} isn't a boolean this test can read{UPDATE}")


def module_of(expression: str) -> str:
    match = re.fullmatch(r"module\.(\w+)\.name", expression)
    if not match:
        raise ValueError(f"repository {expression!r} isn't module.<name>.name{UPDATE}")
    return match.group(1)


def object_map(expression: str) -> dict[str, dict[str, bool]]:
    """A local like `{ "a" = { x = true, y = false } ... }`: string keys, boolean fields."""
    entry = re.compile(r'"([^"]+)"\s*=\s*\{([^{}]*)\}')
    rest = entry.sub("", expression)
    if rest.replace(",", "").split() != ["{", "}"]:
        raise ValueError(f"the local {expression[:40]!r} isn't a map of objects{UPDATE}")
    result = {}
    for key, fields in entry.findall(expression):
        pairs = [pair.split("=") for pair in fields.split(",") if pair.strip()]
        result[key] = {name.strip(): boolean(value.strip(), None) for name, value in pairs}
    return result


def nested(resource: Block, kind: str, entry: dict[str, bool] | None) -> list[Block]:
    """A resource's `kind` blocks: literal, or `dynamic` on `each.value.<k> ? [1] : []`."""
    found = [block for block in resource.blocks if block.type == kind]
    for dynamic in resource.blocks:
        if dynamic.type != "dynamic" or dynamic.labels != (kind,):
            continue
        condition = re.fullmatch(
            r"each\.value\.(\w+) \? \[1\] : \[\]", dynamic.attrs.get("for_each", "")
        )
        content = [block for block in dynamic.blocks if block.type == "content"]
        if not condition or entry is None or condition.group(1) not in entry or len(content) != 1:
            raise ValueError(f"can't read the dynamic {kind!r} block{UPDATE}")
        if entry[condition.group(1)]:
            found.append(content[0])
    return found


def environment(resource: Block, name: str, entry: dict[str, bool] | None) -> Environment:
    policies = nested(resource, "deployment_branch_policy", entry)
    users = []
    for reviewers in nested(resource, "reviewers", entry):
        listed = re.fullmatch(r"\[(.*)\]", reviewers.attrs.get("users", ""))
        if not listed:
            raise ValueError(f"{name}'s reviewers aren't a list{UPDATE}")
        users += [user.strip() for user in listed.group(1).split(",") if user.strip()]
    return Environment(
        name=name,
        repository=module_of(resource.attrs["repository"]),
        # Unset, GitHub lets admins bypass the environment.
        can_admins_bypass=boolean(resource.attrs.get("can_admins_bypass", "true"), entry),
        branch_policy=policies[0] if policies else None,
        reviewers=tuple(users),
    )


def declarations(
    texts: dict[str, str],
) -> tuple[list[Environment], dict[tuple[str, str], list[str]]]:
    """Every declared environment, and the branch patterns declared for each (repository, name)."""
    blocks = [block for text in texts.values() for block in parse(text).blocks]
    locals_ = {
        name: value
        for block in blocks
        if block.type == "locals"
        for name, value in block.attrs.items()
    }
    resources = {
        block.labels: block
        for block in blocks
        if block.type == "resource" and len(block.labels) == 2
    }

    def instances(label: str) -> dict[str, dict[str, bool] | None]:
        """An environment resource's instances: its name for each, and its for_each entry."""
        resource = resources.get(("github_repository_environment", label))
        if resource is None:
            raise ValueError(f"github_repository_environment.{label} isn't declared")
        if "for_each" not in resource.attrs:
            return {literal_string(resource.attrs["environment"]): None}
        source = re.fullmatch(r"local\.(\w+)", resource.attrs["for_each"])
        if (
            not source
            or source.group(1) not in locals_
            or resource.attrs["environment"] != "each.key"
        ):
            raise ValueError(f"can't read github_repository_environment.{label}'s for_each{UPDATE}")
        return dict(object_map(locals_[source.group(1)]))

    environments = [
        environment(resource, name, entry)
        for (kind, label), resource in resources.items()
        if kind == "github_repository_environment"
        for name, entry in instances(label).items()
    ]

    patterns: dict[tuple[str, str], list[str]] = {}
    for (kind, label), policy in resources.items():
        if kind != "github_repository_environment_deployment_policy":
            continue
        target = policy.attrs["environment"]
        single = re.fullmatch(r"github_repository_environment\.(\w+)\.environment", target)
        each = re.fullmatch(
            r"github_repository_environment\.(\w+)\[each\.key\]\.environment", target
        )
        if single:
            names = list(instances(single.group(1)))
        elif each:
            names = filtered_keys(policy.attrs.get("for_each", ""), locals_, label)
            names = [name for name in names if name in instances(each.group(1))]
        elif target.startswith('"'):
            names = [literal_string(target)]
        else:
            raise ValueError(f"can't read the environment of policy {label}{UPDATE}")
        repository = module_of(policy.attrs["repository"])
        for name in names:
            patterns.setdefault((repository, name), []).append(
                literal_string(policy.attrs["branch_pattern"])
            )
    return environments, patterns


def filtered_keys(for_each: str, locals_: dict[str, str], label: str) -> list[str]:
    """The keys of `{ for name, env in local.<map> : name => env if env.<field> }`."""
    match = re.fullmatch(
        r"\{ for (\w+), (\w+) in local\.(\w+) : \1 => \2 if \2\.(\w+) \}", for_each
    )
    if not match or match.group(3) not in locals_:
        raise ValueError(f"can't read policy {label}'s for_each{UPDATE}")
    entries = object_map(locals_[match.group(3)])
    return [name for name, entry in entries.items() if entry.get(match.group(4), False)]


def problems(texts: dict[str, str]) -> list[str]:
    """What's wrong with each main-only environment's declaration (design D1, D3)."""
    environments, patterns = declarations(texts)
    found = []
    for (repository, name), owner_reviews in MAIN_ONLY.items():
        expected_on = [module for module, other in MAIN_ONLY if other == name]
        label = f"{name} on {repository}" if len(expected_on) > 1 else name
        here = [env for env in environments if env.name == name]
        on_repository = [env for env in here if env.repository == repository]
        if not on_repository:
            elsewhere = sorted(env.repository for env in here if env.repository not in expected_on)
            found.append(
                f"{label}: declared on {', '.join(elsewhere)}, not {repository}"
                if elsewhere
                else f"{label}: not declared"
            )
            continue
        if len(on_repository) > 1:
            raise ValueError(f"{name} is declared more than once on {repository}")
        env = on_repository[0]
        if env.can_admins_bypass:
            found.append(f"{label}: can_admins_bypass isn't false")
        policy = env.branch_policy
        if policy is None:
            found.append(f"{label}: has no deployment branch policy, so any branch can deploy")
        else:
            if boolean(policy.attrs.get("protected_branches", "true"), None):
                found.append(f"{label}: protected_branches isn't false")
            if not boolean(policy.attrs.get("custom_branch_policies", "false"), None):
                found.append(f"{label}: custom_branch_policies isn't true")
        declared = sorted(patterns.get((repository, name), []))
        if declared != ["main"]:
            found.append(f"{label}: its branch policies are {declared}, not ['main']")
        if owner_reviews and "local.owner_user_id" not in env.reviewers:
            found.append(f"{label}: the owner isn't a required reviewer")
    return found


def real_texts() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in TF_FILES}


def edit(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"expected exactly one {old!r}"
    return text.replace(old, new)


def delete_block(text: str, header: str) -> str:
    start = text.index(header)
    end = text.index("\n}\n", start) + len("\n}\n")
    return text[:start] + text[end:]


def edited(file: str, old: str, new: str) -> dict[str, str]:
    texts = real_texts()
    texts[file] = edit(texts[file], old, new)
    return texts


PAGES = 'resource "github_repository_environment" "github_pages" {'
PAGES_POLICY = (
    'resource "github_repository_environment_deployment_policy" "github_pages_main_only" {'
)
RELEASE = 'resource "github_repository_environment" "release" {'
RELEASE_POLICY = 'resource "github_repository_environment_deployment_policy" "release_main_only" {'
BOARD = 'resource "github_repository_environment" "board" {'
BOARD_POLICY = 'resource "github_repository_environment_deployment_policy" "board_main_only" {'
BOARD_INFRASTRUCTURE = 'resource "github_repository_environment" "board_infrastructure" {'
BOARD_INFRASTRUCTURE_POLICY = (
    'resource "github_repository_environment_deployment_policy" "board_infrastructure_main_only" {'
)
CI_BYPASS = "can_admins_bypass   = false\n  prevent_self_review = false\n\n  dynamic"
PAGES_BYPASS = (
    "can_admins_bypass   = false\n  prevent_self_review = false\n\n  deployment_branch_policy {"
)


def test_the_declared_environments_are_main_only() -> None:
    assert problems(real_texts()) == []


def test_a_deleted_pages_declaration_is_named() -> None:
    """#61's case: the block and its policy deleted, which prevent_destroy didn't stop."""
    texts = real_texts()
    texts["environments.tf"] = delete_block(
        delete_block(texts["environments.tf"], PAGES), PAGES_POLICY
    )
    assert problems(texts) == ["github-pages: not declared"]


def test_a_commented_out_declaration_is_not_declared() -> None:
    texts = real_texts()
    text = texts["environments.tf"]
    start = text.index(PAGES)
    texts["environments.tf"] = text[:start] + "".join(
        f"# {line}" for line in text[start:].splitlines(keepends=True)
    )
    assert problems(texts) == ["github-pages: not declared"]


def test_a_deleted_release_declaration_is_named() -> None:
    texts = real_texts()
    texts["release.tf"] = delete_block(delete_block(texts["release.tf"], RELEASE), RELEASE_POLICY)
    assert problems(texts) == ["release: not declared"]


def test_a_deleted_board_declaration_is_named() -> None:
    texts = real_texts()
    texts["board.tf"] = delete_block(delete_block(texts["board.tf"], BOARD), BOARD_POLICY)
    assert problems(texts) == ["board on repo_website: not declared"]


def test_a_deleted_infrastructure_board_declaration_is_named() -> None:
    """The other board still declared on website doesn't count for infrastructure's."""
    texts = real_texts()
    texts["board.tf"] = delete_block(
        delete_block(texts["board.tf"], BOARD_INFRASTRUCTURE), BOARD_INFRASTRUCTURE_POLICY
    )
    assert problems(texts) == ["board on repo_infrastructure: not declared"]


def test_infrastructure_s_board_open_to_an_admin_bypass_is_named() -> None:
    texts = real_texts()
    text = texts["board.tf"]
    start = text.index(BOARD_INFRASTRUCTURE)
    texts["board.tf"] = text[:start] + edit(
        text[start:], "can_admins_bypass   = false", "can_admins_bypass   = true"
    )
    assert problems(texts) == ["board on repo_infrastructure: can_admins_bypass isn't false"]


def test_apply_dropped_from_the_ci_environments_is_named() -> None:
    texts = edited(
        "environments.tf", '    "apply"     = { approval = true, main_only = true }\n', ""
    )
    assert problems(texts) == ["apply: not declared"]


def test_plan_main_no_longer_main_only_is_named() -> None:
    texts = edited(
        "environments.tf",
        '"plan-main" = { approval = false, main_only = true }',
        '"plan-main" = { approval = false, main_only = false }',
    )
    assert problems(texts) == [
        "plan-main: has no deployment branch policy, so any branch can deploy",
        "plan-main: its branch policies are [], not ['main']",
    ]


def test_an_admin_bypass_on_ci_s_environments_is_named() -> None:
    texts = edited("environments.tf", CI_BYPASS, CI_BYPASS.replace("false", "true", 1))
    assert problems(texts) == [
        "plan-main: can_admins_bypass isn't false",
        "apply: can_admins_bypass isn't false",
    ]


def test_an_admin_bypass_on_pages_is_named() -> None:
    texts = edited("environments.tf", PAGES_BYPASS, PAGES_BYPASS.replace("false", "true", 1))
    assert problems(texts) == ["github-pages: can_admins_bypass isn't false"]


def test_an_unset_admin_bypass_is_named_since_github_s_default_allows_it() -> None:
    texts = edited("release.tf", "  can_admins_bypass   = false\n", "")
    assert problems(texts) == ["release: can_admins_bypass isn't false"]


def test_release_following_protected_branches_is_named() -> None:
    texts = edited("release.tf", "protected_branches     = false", "protected_branches     = true")
    assert problems(texts) == ["release: protected_branches isn't false"]


def test_pages_without_custom_branch_policies_is_named() -> None:
    texts = real_texts()
    text = texts["environments.tf"]
    start = text.index(PAGES)
    texts["environments.tf"] = text[:start] + edit(
        text[start:], "custom_branch_policies = true", "custom_branch_policies = false"
    )
    assert problems(texts) == ["github-pages: custom_branch_policies isn't true"]


def test_a_deleted_main_only_policy_is_named() -> None:
    texts = real_texts()
    texts["release.tf"] = delete_block(texts["release.tf"], RELEASE_POLICY)
    assert problems(texts) == ["release: its branch policies are [], not ['main']"]


def test_a_widened_branch_pattern_is_named() -> None:
    texts = edited(
        "environments.tf",
        'github_pages.environment\n  branch_pattern = "main"',
        'github_pages.environment\n  branch_pattern = "*"',
    )
    assert problems(texts) == ["github-pages: its branch policies are ['*'], not ['main']"]


def test_a_second_branch_policy_is_named() -> None:
    texts = real_texts()
    texts["release.tf"] += (
        '\nresource "github_repository_environment_deployment_policy" "release_too" {\n'
        "  repository     = module.repo_troupe.name\n"
        "  environment    = github_repository_environment.release.environment\n"
        '  branch_pattern = "release/*"\n'
        "}\n"
    )
    assert problems(texts) == [
        "release: its branch policies are ['main', 'release/*'], not ['main']"
    ]


def test_apply_without_approval_is_named() -> None:
    texts = edited(
        "environments.tf",
        '"apply"     = { approval = true, main_only = true }',
        '"apply"     = { approval = false, main_only = true }',
    )
    assert problems(texts) == ["apply: the owner isn't a required reviewer"]


def test_apply_with_no_reviewer_users_is_named() -> None:
    texts = edited("environments.tf", "users = [local.owner_user_id]", "users = []")
    assert problems(texts) == ["apply: the owner isn't a required reviewer"]


def test_pages_moved_to_another_repository_is_named() -> None:
    texts = edited(
        "environments.tf",
        'repository  = module.repo_website.name\n  environment = "github-pages"',
        'repository  = module.repo_troupe.name\n  environment = "github-pages"',
    )
    assert problems(texts) == ["github-pages: declared on repo_troupe, not repo_website"]


def test_a_dynamic_condition_it_can_t_read_is_refused_rather_than_guessed() -> None:
    texts = edited(
        "environments.tf",
        "for_each = each.value.main_only ? [1] : []",
        "for_each = each.value.main_only == true ? [1] : []",
    )
    with pytest.raises(ValueError, match="update this test"):
        problems(texts)


def test_a_computed_admin_bypass_is_refused_rather_than_guessed() -> None:
    texts = edited("environments.tf", CI_BYPASS, CI_BYPASS.replace("false", "local.bypass", 1))
    with pytest.raises(ValueError, match="update this test"):
        problems(texts)
