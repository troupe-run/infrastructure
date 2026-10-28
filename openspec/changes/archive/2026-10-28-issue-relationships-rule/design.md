# Design

## Context

- `org-profile/CONTRIBUTING.md` is delivered to `troupe-run/.github` by `tofu/org_profile.tf`. A change to it shows in
  the plan as one in-place update of `github_repository_file.org_profile["CONTRIBUTING.md"]`.
- The org's issue types are declared in `oob/issue-types.json` (Task, Bug, Feature, Epic, Decision, all enabled),
  and `scripts/oob.py` compares that file with GitHub. `scripts/tests/test_org_profile.py` already checks each issue
  form's `type:` against it, and checks the guide's sign-off table against `tofu/required-checks.json`. The new test
  follows the same pattern.
- The forms set Feature, Bug and Decision. Task and Epic have no form. Setting a type by hand takes triage access,
  so an outside contributor can't, and a maintainer does it.
- The guard already lets agents add sub-issues and blocked-by links with `gh issue edit --add-sub-issue` and
  `--add-blocked-by`, so the rule asks for nothing an agent can't do.
- The Milestones section says completed work takes "the one of the work it arose from". Today nothing says how that
  origin is recorded.

## Goals / Non-Goals

**Goals:**

- A contributor reading the guide knows which relationship to use, and files work found mid-change as one piece of
  work with its origin.
- The guide's list of types can't drift from the org's.

**Non-Goals:**

- Re-linking existing issues. The 2026-10-26 sweep already did that.
- Saying how the board shows Epics. The board's views are a separate concern.

## Decisions

### D1. The section's text, and where it goes

A new `## How issues are related` section goes straight before `## Milestones`, because the milestone rule reads its
"arose from" line. The text:

> Work often grows while it's being done. Relate issues so that it still reads as one piece of work, whichever
> repositories it's in. Each relationship answers one question:
>
> - **Sub-issue of an Epic:** the parts of one outcome, in any repository. It answers "is the outcome done?" An issue
>   with sub-issues is an Epic, and it's done when every sub-issue is.
> - **Blocked by:** a real prerequisite, a Decision included. It answers "can this start?"
> - **"Arose from" in the body:** where a follow-up came from, as a line such as
>   `Arose from troupe-run/troupe#139.` The milestone rule below reads it.
>
> Work found while doing a change becomes a sub-issue of the Epic its origin belongs to, so the Epic isn't done
> until that work is, and it gets the "arose from" line too. When the origin has no Epic, or the follow-up isn't
> needed for the outcome (it's parked, optional, or a new outcome of its own), it gets only the "arose from" line.
>
> Every issue has a type: Epic, Feature, Bug, Task or Decision.

Two smaller edits:

- **How work flows, step 1:** after "Use the Feature, Bug or Decision form", add "A Task or an Epic has no form: a
  maintainer sets its type."
- **Milestones:** "the one of the work it arose from" links to `#how-issues-are-related`.

Alternatives: putting the rule inside "How work flows" step 1 makes that step long, and splits it from the milestone
rule that depends on it. A separate section next to Milestones is what #149 asks for.

### D2. The issue-type test

A function in `scripts/tests/test_org_profile.py` takes the guide's text and the enabled types, and returns the
problems, each naming the type. It finds the line that starts `Every issue has a type:` and reads the names from the
rest of that sentence, split on commas and `or`. The real-guide test passes the guide and
`enabled_types(ISSUE_TYPES)`. Fixture tests cover each scenario in the spec: a sound list, a type the org lacks, a
type the guide leaves out, and no list at all.

The test doesn't call GitHub. `oob/issue-types.json` is already compared with GitHub by `oob.py`, so checking against
the file keeps `scripts/check.py` offline, as the other org-profile tests are.

Alternative: no test. The list would then drift silently the first time a type is added, and nothing would say so.

### D3. Owner decision: the issue forms stay as they are (recommended)

#149 asks whether the forms should offer an Epic form or a "Part of" field. The recommendation is neither, for now:

- An issue form can't set a parent. A "Part of" field would be text in the body, which is the flat linking the
  2026-10-26 review found didn't work. The link that counts is the sub-issue, which is made after the issue exists.
- Epics are made by maintainers when they plan an outcome, not filed by contributors, so a form adds a file to keep
  in step without anyone needing it.
- Changing a form would put a second file in the plan, against #149's "Done when".

If the owner wants an optional "Arose from" field on the Feature and Bug forms, so the line is prompted for, that's a
follow-up issue: it changes those forms and their tests, not this guide.

### D4. Owner decision: no enforcement in this change (recommended)

#149 asks whether the guard, or a check, should refuse an issue with sub-issues that isn't an Epic, or an issue with
no type. The recommendation is not here:

- The guard judges commands as they run. It could refuse `gh issue create` without `--type`, but not an issue made
  in the browser, and not a sub-issue added to a Task later. A refusal that only some routes hit is a partial rule.
- A complete check would read every issue's type and sub-issues on a schedule and report what's wrong, much as
  `oob.py` reports settings. That's a new job with its own tests and credentials, and its own issue.

If the owner wants it, a follow-up issue goes on the board, with this change named in its "arose from" line.

## Risks / Trade-offs

- [The guide states a rule nothing enforces] → It says what reviewers and agents check. D4's follow-up issue is how
  it gets enforced, if the owner wants that.
- [The test reads one sentence, so rewording breaks it] → The test fails saying the list wasn't found, which names
  the cause. Rewording the sentence means changing the test with it, in the same pull request.

## Migration Plan

Merge, then the owner approves `main`'s apply. One commit to `CONTRIBUTING.md` in `troupe-run/.github`. To roll back,
revert the pull request and apply again.
