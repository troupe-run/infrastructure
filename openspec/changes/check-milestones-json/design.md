# Design

## Context

See proposal.md for why.

- **The website's rules** are `readRoadmap` in troupe-run/website's `scripts/roadmap-lib.mjs` (read on `origin/main`,
  2026-10-25), from its archived change `2026-10-23-status-roadmap-releases`, design D4. In the order it checks them,
  it refuses:
  1. text that `JSON.parse` refuses;
  2. a top level that isn't a non-array object, or whose `milestones` isn't an array;
  3. an entry that isn't a non-null, non-array object (named `milestone <i+1>`);
  4. a `title` that isn't a string matching `^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$`;
  5. a `description` that isn't a string, or whose `trim()` is empty;
  6. a title seen before.

  It stops at the first problem. It reads nothing else.
- **This repository's check** is `declaration_problems` in `scripts/tests/test_milestones.py`, run by `scripts/check.py`.
  It returns one message per problem and already covers rule 6. `test_the_declared_milestones_are_well_formed` reads
  the real file with `json.loads` and asserts there are no problems. The `milestones` scope in
  `scripts/check-paths.toml` means the required `check` job runs these tests whenever a pull request changes
  `tofu/milestones.json`.
- **Today the check crashes on a malformed milestone.** It indexes `milestone["key"]`, `["title"]`, `["state"]` and
  `["description"]`, so a missing field is a `KeyError` and a non-object entry a `TypeError`. The test still fails, but
  with a traceback that names neither the milestone nor the fix.
- `tofu/milestones.tf` reads the file with `jsondecode`, so the plan already fails on text that isn't JSON (rule 1).
  `scripts/oob.py` reads the titles too. Neither changes.

## Goals / Non-Goals

**Goals:**

- Every file the website would refuse fails `scripts/check.py`, with a message that names the milestone and the fix.
- Every file `scripts/check.py` accepts, the website accepts.

**Non-Goals:**

- Reporting every problem in a file whose shape is wrong. Once the top level or an entry isn't an object, the rules
  that read its fields don't run for it.
- Matching the website's messages word for word. Each side words its own messages.

## Decisions

### D1. Copy the rules from the website's code, not from the issue

Each rule is written from `readRoadmap` (Context, rules 1 to 6), not from #125's summary, because the build is what
stops the site. The two agree, but the code is more exact in two places that matter in Python:

- **Title.** `\d` in a JavaScript regex without the `u` flag is ASCII only, and `$` matches only at the end. In Python,
  `\d` also matches other digits, such as Arabic-Indic `٣`, and `$` also matches before a final newline. So the check
  uses `re.fullmatch` with `[0-9]`: `(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)`.
- **Empty description.** JavaScript's `trim()` and Python's `str.strip()` strip slightly different characters. `trim()`
  also strips U+FEFF, and `strip()` also strips `\x1c`–`\x1f` and `\x85`. The check counts a description as empty when
  every character is either `str.isspace()` or U+FEFF. That refuses everything the website refuses, plus a description
  made only of those five control characters, which no one writes on purpose.
- **JSON.** Python's `json` accepts `NaN`, `Infinity` and `-Infinity`, and `JSON.parse` doesn't. The test that reads
  the real file passes a `parse_constant` that raises, naming the file. The plan's `jsondecode` refuses them too, so
  this only gives a clearer message earlier.

**Why:** the issue's rules are a summary, and #125 says to change both sides together. Copying from the code is the
only way the two sides agree on edge cases neither side wrote down. Before relying on it, the apply runs the
website's `readRoadmap` on the same cases as the new tests (tasks 2.1), so the agreement is tested, not assumed.

**Alternative:** run the website's code from this repository's CI. That means cloning troupe-run/website and running
Node in a Python-only check that must work offline. Rejected: the rules are short, and a pointer on each side (D4) is
enough to keep them in step.

### D2. Extend the existing declaration check

The new rules go into `scripts/tests/test_milestones.py`, beside the rules for keys, states, interim titles and quotes.

- **Why:** it already runs on every pull request that touches the file, through a required check. Its messages
  already name milestones by title. It's where the milestones spec says the declaration's rules live.
- **Alternative:** OpenTofu `precondition`s or `check` blocks in `tofu/milestones.tf`. The plan runs on every pull
  request too, but the messages are worse and they'd split the declaration's rules between two places. Rejected.
- **Alternative:** a separate script under `scripts/`. Nothing else needs to call it. Rejected.

### D3. Check the shape first, then each milestone, and never crash

The check runs in two layers:

1. **Shape.** A function takes the parsed file and returns the list of milestones, or a single problem: the top
   level isn't an object, or its `milestones` isn't an array. With a shape problem, nothing else runs. A new test
   asserts the real file has the right shape before `declaration_problems` runs on it.
2. **Each milestone.** `declaration_problems` takes the list. An entry that isn't an object gets one problem,
   `milestone <n>: …`, and no other rule reads it. For each object, the title and description rules run, and the
   existing rules read each field with `.get` and skip a field that's missing or isn't a string, rather than crash.

A milestone is named by its title when its title is a string, or `milestone <n>` (counting from 1, as the website
does) when it isn't. Messages follow the existing style: `<name>: <what's wrong>; <fix>`. For example:

```
milestone 3: isn't an object; each milestone must be an object with a title and a description
v0.3.0: title 'v0.3.0' isn't a version; title it MAJOR.MINOR.PATCH, with no leading zeros or "v", as in "0.3.0"
milestone 2: title 3 isn't a version; title it MAJOR.MINOR.PATCH, with no leading zeros or "v", as in "0.3.0"
0.4.0: description is empty; describe what the milestone adds for a user
```

- **Why:** a person reading the check's output should see what to change, not a traceback, and one bad milestone
  shouldn't hide the problems in the others. Naming by title matches every existing message. Positions are only for
  milestones that have no usable title.
- **What doesn't change:** missing `key` and `state` aren't reported by name. The website doesn't read them, the plan
  already fails on them, and #125 doesn't ask for it.

### D4. Each copy of the rules points at the other

The rules section of `declaration_problems` gets a comment naming troupe-run/website's `scripts/roadmap-lib.mjs`
(`readRoadmap`) and its design D4, and saying a rule changed here must change there too. The website's code says
where the file comes from but not that the rules are copied here. Adding that is the website's call, so the comment
on #125 after the merge says this check exists and suggests the website point back at it.

- **Why:** #125 asks for the two to change together, and nothing automatic can keep them in step (D1).

## Risks / Trade-offs

- [The website adds a rule and this check doesn't] → D4's pointer, and the website's build still fails safe: a bad
  file stops the deploy, it doesn't publish a bad page.
- [This check refuses something the website accepts] → only the five control characters in D1, which no description
  needs. Every other case is tested against the website's code in tasks 2.1.
- [Messages differ between the two sides] → each names the milestone and the fix, which is what someone needs to act.

## Migration Plan

No migration. The real file passes the new rules today (21 milestones, checked 2026-10-25). The change touches only
`scripts/tests/` and `openspec/`, which `scripts/plan_needed.py` lists as never read by OpenTofu, so no plan runs and
there's nothing to apply.
