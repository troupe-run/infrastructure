# Proposal

Issue: #125.

## Why

Since troupe-run/website#32 (`status-roadmap-releases`), every troupe.run build reads this repository's
`tofu/milestones.json` from `main` and fails when the file breaks the website's rules. A bad edit that merges here
blocks every deploy of the site, `/docs` included, until someone fixes it here. Since #124, that merge also starts a
website deploy straight away, so the failure shows up within minutes.

This repository's check already catches some of what the website refuses: invalid JSON (the plan's `jsondecode`, and
the milestone tests' `json.loads`) and two milestones with the same title (`declaration_problems`). It doesn't catch
the rest. A title such as `v0.3` or `0.03.0`, an empty description, or a milestone that isn't an object all pass here
and stop the site after the merge.

## What Changes

- **The milestone check enforces every rule the website's build enforces**, on every pull request, through
  `scripts/check.py` and the required `check` job, which already runs the milestone tests whenever the file changes.
  The rules are the website's `readRoadmap` in `scripts/roadmap-lib.mjs` (its design D4), read from its code rather
  than from the issue (design D1):
  - the file is JSON, and its top level is an object with a `milestones` array;
  - every milestone is an object;
  - every `title` is a string of the form `MAJOR.MINOR.PATCH`: ASCII digits, no leading zeros, no `v`, nothing before
    or after (`0.3.0`, not `v0.3.0`, `0.3` or `0.03.0`);
  - no two milestones share a title (already checked; unchanged);
  - every `description` is a string with something in it besides whitespace.
- **Each failure names the milestone and the fix.** A milestone is named by its title when the title is a string, and
  by its position in the file otherwise (design D3).
- **A malformed milestone fails with a message, not a crash.** Today a milestone with no `description`, or one that
  isn't an object, stops the test with a `KeyError` or `TypeError` traceback. The existing rules skip a field that's
  missing or the wrong type, and the new rules report it (design D3).
- **Each copy of the rules points at the other**, so a change on one side is made on both, as #125 asks (design D4).

Out of scope:

- Keys the website ignores (`key`, `state`, `interim_title`, `repositories`). Their existing rules stay as they are.
  A missing `key` or `state` still fails the plan, as it does today.
- Changing the website. Its rules and messages stay as they are. Whether its code should point back here is for the
  website's owner (design D4).
- Making the plan itself enforce these rules (OpenTofu `precondition`s). The check already runs on every pull request
  and gives better messages (design D2).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `milestones`: "The milestone declaration is well formed" also fails when the file isn't an object with a
  `milestones` array, when a milestone isn't an object, when a title isn't `MAJOR.MINOR.PATCH`, and when a description
  isn't a string with something in it besides whitespace.

## Impact

- `scripts/tests/test_milestones.py`: the declaration check, its tests, and a test that reads the real file.
- `tofu/milestones.json`: no change. All 21 milestones already pass the new rules.
- No plan and no apply: the change touches only `scripts/tests/` and `openspec/`, which OpenTofu never reads, so the
  pull request needs no plan approval.
- #125 is closed by this change's pull request.
