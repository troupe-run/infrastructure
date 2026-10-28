# Proposal

## Why

On 2026-10-26 a review of all 211 troupe-run issues found that outcomes spanning several issues and repositories had
been filed flat, linked only in issue bodies. The release-milestones work was 15 issues in 3 repositories that read
as unrelated cards on the board. Only 5 parents had sub-issues and 80 issues had no type. Twelve Epics were made
afterwards to link the work (infrastructure#144 to #148, troupe#163 to #168, website#48), and every issue now has a
type. The org's contributing guide doesn't say how issues are related, so the same thing will happen again. The
owner asked for the rule to be written down (#149, 2026-10-26).

## What Changes

- `org-profile/CONTRIBUTING.md` gets a section, **How issues are related**, just before Milestones. It says:
  - each relationship answers one question. A **sub-issue of an Epic** is a part of one outcome, in any repository
    ("is the outcome done?"), and an issue with sub-issues is an Epic. **Blocked by** is a real prerequisite, a
    Decision included ("can this start?"). An **"arose from" line in the body** says where a follow-up came from.
  - work found while doing a change becomes a sub-issue of the Epic its origin belongs to, so that Epic isn't done
    until the work is, and it gets the "arose from" line too. When the origin has no Epic, or the follow-up isn't
    needed for the outcome (parked, optional, or a new outcome of its own), it gets only the "arose from" line.
  - every issue has a type: Epic, Feature, Bug, Task or Decision.
- The Milestones section's "the work it arose from" links to the new section, so both rules read the same line.
- "How work flows" step 1 says that Task and Epic have no form, and that a maintainer sets those types.
- A test checks that the types the guide lists are exactly the enabled issue types in `oob/issue-types.json`, so the
  guide can't name a type the org doesn't have, or leave one out.

Not in this change, and raised with the owner in design D3 and D4:

- **No new issue form and no "Part of" field.** A form can't make a sub-issue, so a "Part of" field would be the same
  link in the body that the review found doesn't work. Changing a form would also put a second file in the plan,
  and #149's "Done when" names only `CONTRIBUTING.md`.
- **No enforcement.** Nothing refuses an issue with sub-issues that isn't an Epic, or an issue with no type. If the
  owner wants that, it becomes a follow-up issue (design D4).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `org-profile`: adds two requirements. The guide says how issues are related, and the guide's issue types are the
  org's enabled issue types.

## Impact

- `org-profile/CONTRIBUTING.md`: the new section, and two small edits in "How work flows" and Milestones.
- `scripts/tests/test_org_profile.py`: the issue-type test, with fixture tests.
- `troupe-run/.github`: one commit to `CONTRIBUTING.md` when `main` is applied. The plan shows only
  `github_repository_file.org_profile["CONTRIBUTING.md"]` changing.
- No guard file changes, so there's no guard delivery to troupe or website.
