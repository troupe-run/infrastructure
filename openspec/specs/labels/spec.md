# labels Specification

## Purpose

Declares each managed repository's complete set of issue labels (name, colour and description) so labels are
changed through pull requests and labels made by hand show up as drift.

## Requirements

### Requirement: Each managed repository's labels are declared in full
Each managed repository's labels SHALL be declared as a complete set: name, colour and description. A label on
GitHub that isn't declared, or that differs from its declaration, SHALL appear in the plan.

#### Scenario: A label added by hand shows as drift
- **WHEN** someone adds a label to a managed repository on GitHub
- **THEN** the next plan shows that label being removed

#### Scenario: A label's colour changed by hand shows as drift
- **WHEN** someone changes a declared label's colour on GitHub
- **THEN** the next plan shows the colour changing back

### Requirement: Adopted labels match GitHub exactly
The labels declared when a repository is adopted SHALL be the labels it had at that moment, unchanged, including
GitHub's default labels and troupe's `cap:*` labels.

#### Scenario: troupe's labels are adopted unchanged
- **WHEN** troupe's labels are adopted and a plan runs
- **THEN** the plan shows no change to any of troupe's labels

### Requirement: Every managed repository has the workflow's labels
The labels the workflow uses, such as `needs:owner`, which the Decision form applies, SHALL be declared once and
SHALL be part of every managed repository's label set, with the same colour and description in each.

#### Scenario: A repository without the label
- **WHEN** a plan runs for a managed repository that has no `needs:owner` label on GitHub
- **THEN** the plan shows `needs:owner` being created there, with the declared colour and description

#### Scenario: troupe's existing label is kept
- **WHEN** troupe's `needs:owner`, which it already had, is declared from the shared list and a plan runs
- **THEN** the plan shows no change to troupe's `needs:owner`

### Requirement: troupe's capability labels are declared here
troupe's `cap:*` labels SHALL be declared in this repository and SHALL change only by a pull request here. troupe
keeps no separate capability list: a new capability gets its label by a pull request that adds it to the
declaration, and the label is created when the owner approves the plan.

#### Scenario: A new capability gets a label
- **WHEN** a pull request adds `cap:<name>` to troupe's declared labels and a plan runs
- **THEN** the plan shows `cap:<name>` being created on troupe-run/troupe, with the declared colour and description,
  and no other label changing

#### Scenario: A capability label made by hand
- **WHEN** someone creates a `cap:*` label on troupe-run/troupe on GitHub without declaring it
- **THEN** the next plan shows that label being removed

### Requirement: A new capability label is a standard change
A new troupe capability label SHALL be added by the standard steps written once in this repository, from a
sub-issue that carries them as its checklist, so each label goes through the same steps. They SHALL leave to the
owner only approving the pull request's plan, adding the board's option just before merging, merging, and approving
the apply.

#### Scenario: The steps a label goes through
- **WHEN** someone adds `cap:workspaces`, which troupe-run/troupe#42 needs
- **THEN** a Task sub-issue holds the steps as a checklist, the change `add-cap-workspaces-label` is archived on its
  branch before its pull request opens, and the pull request closes the sub-issue

#### Scenario: Where the sub-issue sits
- **WHEN** troupe-run/troupe#42 is a sub-issue of the Epic troupe-run/troupe#40, in milestone `0.4.0`
- **THEN** the label's sub-issue is a sub-issue of troupe-run/troupe#40, in milestone `0.4.0`, on the troupe roadmap
  board, and troupe-run/troupe#42 is blocked by it

#### Scenario: A label already declared or under way
- **WHEN** the label is already declared on `main`, or an open issue or pull request already adds it
- **THEN** the steps' first check finds it, and nothing is made

#### Scenario: The board's option comes with the merge
- **WHEN** the owner has approved the pull request's plan and is about to merge it
- **THEN** the steps have the owner add `workspaces` to the board's `Capability` field first, so the drift check that
  runs after the merge finds the label and the option both there

#### Scenario: After the apply
- **WHEN** the apply has created `cap:workspaces`
- **THEN** troupe-run/troupe#42 gets the label with its other labels unchanged, and the sub-issue is closed with its
  card Done and a comment naming the pull request and the change

### Requirement: A capability label in use is never removed or renamed
A `cap:*` label that any troupe issue or pull request carries, open or closed, SHALL NOT be removed from the
declaration or renamed, because removing the declared label deletes it from GitHub and takes it off every issue
that carries it, and a rename is a removal and a creation.

#### Scenario: Removing a label that issues carry
- **WHEN** a pull request removes or renames a declared `cap:*` label
- **THEN** its description lists the troupe issues and pull requests that carry the label, read from GitHub when
  the pull request is opened, and it isn't merged while that list is not empty

### Requirement: A folded capability label is replaced before it's removed
When no troupe spec names a declared `cap:*` label any more, because its spec now names other labels, every troupe
issue and pull request that carries it, open or closed, SHALL first get every label that spec now names, and then
lose the folded label. The label SHALL be removed from the declaration only once it's on nothing.

#### Scenario: A folded label whose spec names two labels
- **WHEN** troupe's `run-workspaces` spec names `cap:stages` and `cap:vcs`, and an issue carries
  `cap:run-workspaces` and `cap:stages`
- **THEN** the issue is given `cap:vcs`, then `cap:run-workspaces` is taken off it, and it keeps `cap:stages`

#### Scenario: Removing folded labels that are on nothing
- **WHEN** a pull request removes folded labels from troupe's declaration, and no troupe issue or pull request carries
  any of them
- **THEN** the plan deletes exactly those labels, changes no other label, and no issue or pull request loses a label

#### Scenario: A folded label still in use
- **WHEN** a pull request removes a folded label that a troupe issue still carries
- **THEN** its description lists that issue, and it isn't merged until the issue has been given the spec's labels and
  the folded label has been taken off it

### Requirement: A troupe spec with no capability label is reported
The out-of-band drift check SHALL read the capability labels that each spec in troupe's `openspec/specs/` on `main`
names in the first non-blank line of its `## Purpose`. It SHALL report a spec that names no label, and a label it
names that isn't declared in `tofu/labels/troupe.json`, naming the spec. A declared label that no spec names SHALL
NOT be reported, since a label can come before its spec.

#### Scenario: A spec without a label
- **WHEN** the first non-blank line of the Purpose of troupe's `cli` spec isn't a `Capability:` line
- **THEN** the drift check prints a difference naming `cli` and saying it names no capability label, and exits 1

#### Scenario: A spec that names an undeclared label
- **WHEN** troupe's `flake-hunt` spec names `cap:development` and troupe's declared labels have no
  `cap:development`
- **THEN** the drift check prints a difference naming `flake-hunt`, `cap:development` and `tofu/labels/troupe.json`,
  and exits 1

#### Scenario: A spec that names two labels
- **WHEN** troupe's `runner-protocol` spec names `cap:actor-runners` and `cap:protocol`, and both are declared
- **THEN** the drift check reports nothing about `runner-protocol`'s labels

#### Scenario: A label ahead of its spec
- **WHEN** troupe's declared labels include `cap:cues` and no troupe spec names it
- **THEN** the drift check reports nothing about `cap:cues`

#### Scenario: A folder without a label of its own name
- **WHEN** troupe's `artifact-store` spec names `cap:storage`, which is declared, and no `cap:artifact-store` is
  declared
- **THEN** the drift check reports nothing about `artifact-store`'s labels

#### Scenario: Every spec has a label
- **WHEN** every spec in troupe's `openspec/specs/` names at least one label, and every label named is declared
- **THEN** the drift check reports no difference for troupe's specs

### Requirement: A troupe spec that can't be read is reported by name
When the drift check can't read a troupe spec's `spec.md`, because fetching it failed or its content couldn't be
decoded as base64 or as UTF-8, it SHALL report troupe's specs as unreadable, naming that spec and why. It SHALL NOT
read the spec as naming no label, and SHALL NOT check label descriptions against specs it couldn't read.

#### Scenario: A spec that can't be fetched
- **WHEN** GitHub answers an error for troupe's `cli` spec's `spec.md`
- **THEN** the drift check reports troupe's specs as unreadable, naming `cli` and GitHub's error, and reports no
  difference for them

#### Scenario: A spec whose content isn't base64
- **WHEN** GitHub's content for troupe's `cli` spec's `spec.md` isn't valid base64
- **THEN** the drift check reports troupe's specs as unreadable, naming `cli` and why

#### Scenario: A spec that isn't UTF-8
- **WHEN** troupe's `cli` spec's `spec.md` decodes from base64 to bytes that aren't UTF-8
- **THEN** the drift check reports troupe's specs as unreadable, naming `cli` and why

### Requirement: A malformed Capability line is reported
A first Purpose line that begins with `Capability` or `Capabilities`, in any case, but isn't `Capability: `
followed by one or more distinct labels, each in backticks and separated by `, `, with nothing after the last, SHALL
be reported by the out-of-band drift check as malformed. The report SHALL name the spec, quote the line and give the expected shape. It SHALL never be
read as naming no label, or as naming the labels it seems to.

#### Scenario: Labels without backticks
- **WHEN** the first line of troupe's `stages` spec's Purpose is `Capability: cap:stages`
- **THEN** the drift check prints a difference naming `stages`, quoting the line and giving the expected shape, and
  exits 1

#### Scenario: Text after the last label
- **WHEN** the first line of a spec's Purpose is ``Capability: `cap:vcs` (and git)``
- **THEN** the drift check reports it as malformed, and doesn't check `cap:vcs` against the declared labels

#### Scenario: A label named twice
- **WHEN** the first line of a spec's Purpose is ``Capability: `cap:vcs`, `cap:vcs` ``
- **THEN** the drift check reports it as malformed

### Requirement: A capability label says what it covers
Each of troupe's `cap:*` labels SHALL have a description of at most 100 characters that says what the capability
covers, not one that only repeats its name. Where troupe has not yet defined a capability, its description SHALL be
`TBD` rather than a guess.

#### Scenario: A description that repeats the name
- **WHEN** a declared `cap:<name>` label's description is `Capability: <name>`
- **THEN** `scripts/check.py` fails, naming the label

#### Scenario: A description over GitHub's limit
- **WHEN** a declared `cap:*` label's description is longer than 100 characters
- **THEN** `scripts/check.py` fails, naming the label and its length

#### Scenario: A capability troupe hasn't defined
- **WHEN** a `cap:*` label has no spec, glossary entry or issue that defines it
- **THEN** its declared description is `TBD`, and `scripts/check.py` passes

### Requirement: troupe's capability labels are declared in one form
troupe's declared labels SHALL be in byte order by name, each `cap:*` name SHALL be `cap:` followed by lowercase
letters and digits in words joined by single hyphens, and every `cap:*` label SHALL have the capability colour,
except `cap:infrastructure`, which marks the org's own setup. `scripts/check.py` SHALL fail on a label that breaks
any of these, naming it.

#### Scenario: A label out of order
- **WHEN** `cap:cli` is declared before `cap:claude-code-runner`
- **THEN** `scripts/check.py` fails, naming both labels

#### Scenario: A malformed name
- **WHEN** a declared label is named `cap:Workspaces`, `cap:a--b` or `cap:-a`
- **THEN** `scripts/check.py` fails, naming the label and the form a name takes

#### Scenario: A different colour
- **WHEN** a declared `cap:*` label other than `cap:infrastructure` has a colour that isn't `1D76DB`
- **THEN** `scripts/check.py` fails, naming the label and the colour

#### Scenario: The org's own label
- **WHEN** `cap:infrastructure` is declared with its adopted colour `5319E7`
- **THEN** `scripts/check.py` passes

### Requirement: A description written from a spec records that spec's Purpose
Each spec in troupe's `openspec/specs/` on `main` SHALL have its Purpose recorded in this repository by spec, next to
the other out-of-band declarations, verbatim without its `Capability:` line. A capability label's description SHALL
be written from the Purposes of every spec that names the label.

#### Scenario: A labelled spec with no recorded Purpose
- **WHEN** troupe's `openspec/specs/` on `main` holds `<name>` and no Purpose is recorded for `<name>`
- **THEN** the drift check prints a difference naming `<name>` and the labels it names, saying its Purpose hasn't
  been recorded, and exits 1

#### Scenario: A recorded Purpose with no spec
- **WHEN** a Purpose is recorded for `cues` and troupe has no `openspec/specs/cues/`
- **THEN** the drift check prints a difference naming `cues` and the record, and exits 1

### Requirement: A description that may be stale is reported
The out-of-band drift check SHALL report each troupe spec whose Purpose on `main`, without its `Capability:` line,
differs from the Purpose recorded for it, naming the spec, the labels it names, and where to update the descriptions
and the record. Differences in line wrapping or surrounding whitespace, and changes to the `Capability:` line alone,
SHALL NOT count as a change.

#### Scenario: troupe rewrites a spec's Purpose
- **WHEN** the Purpose of troupe's `runner-protocol` spec on `main` differs from the Purpose recorded for it
- **THEN** the drift check prints a difference naming `runner-protocol`, `cap:actor-runners`, `cap:protocol`,
  `tofu/labels/troupe.json` and the record, and exits 1

#### Scenario: troupe only re-wraps a Purpose
- **WHEN** the Purpose of troupe's `runs` spec differs from the recorded one only in line breaks or spacing
- **THEN** the drift check reports nothing about `runs`' Purpose

#### Scenario: troupe changes only the labels a spec names
- **WHEN** troupe's `config-files` spec's `Capability:` line changes and the rest of its Purpose doesn't
- **THEN** the drift check reports nothing about `config-files`' Purpose

#### Scenario: Every recorded Purpose matches
- **WHEN** every troupe spec's Purpose, without its `Capability:` line, matches the Purpose recorded for it
- **THEN** the drift check reports no difference for troupe's Purposes

### Requirement: The board's capabilities match troupe's capability labels
The out-of-band drift check SHALL report each option of the troupe roadmap board's `Capability` field with no
declared `cap:<option>` label, and each declared `cap:*` label with no option, naming it and saying the owner changes
the field's options.

#### Scenario: A label with no option
- **WHEN** `cap:runs` is declared and the `Capability` field has no `runs` option
- **THEN** the drift check prints a difference naming `runs` and the board, and exits 1

#### Scenario: An option with no label
- **WHEN** the `Capability` field has a `lifecycle` option and no `cap:lifecycle` is declared
- **THEN** the drift check prints a difference naming `lifecycle`, and exits 1

#### Scenario: They match
- **WHEN** the field's options are exactly the declared `cap:*` names without the prefix
- **THEN** the drift check reports no difference for the board's capabilities

### Requirement: An approved apply gives the board's options their labels' descriptions
Each option of the troupe roadmap board's `Capability` field SHALL have its `cap:<option>` label's description, as
declared here. The plan of `main` SHALL list each option whose description differs, and wait for the owner's approval
even when OpenTofu has no change. After the approved apply, the descriptions SHALL be set, changing no option's
identity, name, colour or order. An option with no label SHALL keep its description.

#### Scenario: A description that differs shows in the plan
- **WHEN** `main` is planned while the `runs` option's description is empty and `cap:runs` has a description
- **THEN** the plan's summary names `runs`, its description now and the one it will get, and the run waits for the
  owner's approval

#### Scenario: The approved apply sets it and keeps every card's value
- **WHEN** the owner approves that plan and the apply succeeds
- **THEN** the `runs` option has `cap:runs`'s description, keeps its id, name and colour, and every card that had a
  `Capability` value has the same value afterwards

#### Scenario: Descriptions that already match change nothing
- **WHEN** every option with a label already has its label's description
- **THEN** the plan lists no description to set, and nothing is sent to the board

#### Scenario: A board that can't be read doesn't hold up the apply
- **WHEN** `main` is planned and the `Capability` field can't be read
- **THEN** the plan's summary says the board's descriptions couldn't be read and names why, OpenTofu's changes are
  planned and applied as usual, nothing is sent to the board, and the drift check reports the board as unreadable

#### Scenario: An option with no label is left alone
- **WHEN** the field has a `lifecycle` option and no `cap:lifecycle` is declared
- **THEN** the apply sends `lifecycle` back unchanged, and the drift check reports it as an option with no label

### Requirement: The board's options are never sent without their identity
Setting the descriptions SHALL send every existing option with its id, and SHALL refuse, sending nothing, when any
option to be sent has no id, or when the field's options differ from those the approved plan was made from. The
refusal SHALL name the option or the difference. Setting the descriptions SHALL never create or remove an option.

#### Scenario: An option without its id is refused
- **WHEN** an option to be sent has no id
- **THEN** nothing is sent, and the job fails naming the option

#### Scenario: The field changed since the plan
- **WHEN** the owner adds, removes or renames an option, or edits a description, between the plan and the apply
- **THEN** nothing is sent, the job fails naming what changed, and the next plan of `main` lists the descriptions
  again

#### Scenario: A label with no option gets none
- **WHEN** `cap:workspaces` is declared and the field has no `workspaces` option
- **THEN** the apply creates no option, and the drift check reports the label as having no option

### Requirement: The drift check reports an option whose description differs from its label's
The out-of-band drift check SHALL report each option of the troupe roadmap board's `Capability` field whose
description differs from its `cap:<option>` label's declared description, naming the option and saying that the next
approved apply sets it.

#### Scenario: A stale description
- **WHEN** `cap:runs`'s declared description has changed and the `runs` option still has the old one
- **THEN** the drift check prints a difference naming `runs` and the board, and exits 1

#### Scenario: Matching descriptions
- **WHEN** every option with a label has its label's description
- **THEN** the drift check reports no description difference for the board's capabilities

### Requirement: troupe has release-please's labels
troupe's label set SHALL include `autorelease: pending` and `autorelease: tagged`, declared once in their own set
with a colour and a description, because release-please finds its release pull request by these labels and a label
it made by itself would be removed by the next apply. No other repository SHALL get them until it releases.

#### Scenario: The labels are created on troupe
- **WHEN** a plan runs after the release labels are declared
- **THEN** it shows `autorelease: pending` and `autorelease: tagged` being created on troupe-run/troupe with the
  declared colour and description, and no other label on any repository changing

#### Scenario: A release label edited by hand
- **WHEN** someone changes the colour or description of `autorelease: pending` on troupe on GitHub
- **THEN** the next plan shows it changing back, and the label stays on every pull request that carries it

#### Scenario: Another repository
- **WHEN** a plan runs for infrastructure, `.github` or website
- **THEN** it shows no `autorelease:` label on them

### Requirement: Kinds of work beyond GitHub's defaults are declared once
Labels for a kind of work that any repository can have and that GitHub's default labels don't cover, such as
`speed`, SHALL be declared once, each with a colour and a description of at most 100 characters that says what work
it marks, and SHALL be part of every managed repository's label set, with the same colour and description in each.
A capability label SHALL NOT be used to mark a kind of work.

#### Scenario: The speed label is created everywhere
- **WHEN** a plan runs after `speed` is declared
- **THEN** it shows `speed` being created on troupe, `.github`, infrastructure and website with the declared colour and
  description, and no other label changing

#### Scenario: A kind label's description over GitHub's limit
- **WHEN** a declared kind label's description is longer than 100 characters
- **THEN** `scripts/check.py` fails, naming the label and its length

#### Scenario: A kind label edited by hand
- **WHEN** someone changes `speed`'s colour or description on one repository on GitHub
- **THEN** the next plan shows it changing back there, and the label stays on every issue that carries it

### Requirement: Each repository has the labels Dependabot applies
Each managed repository's label set SHALL include `dependencies` and the label Dependabot applies for each package
ecosystem its dependency graph lists. Each label SHALL be declared once, with the name, colour and description that
GitHub's Dependabot gives it. Dependabot then finds the labels and creates none of its own. A repository whose
dependency graph lists no ecosystem SHALL get none of them.

#### Scenario: website's Dependabot labels are kept
- **WHEN** website's `dependencies` and `javascript` labels, which Dependabot created, are declared and a plan runs
  while its Dependabot pull requests are open
- **THEN** the plan shows no change to either label on website, and the pull requests keep their labels

#### Scenario: The labels are created where Dependabot hasn't run
- **WHEN** a plan runs after the Dependabot labels are declared
- **THEN** it shows `github_actions` created on website, and `dependencies`, `python:uv` and `github_actions`
  created on troupe and infrastructure, each with the declared colour and description, and no other label changing

#### Scenario: A repository with no dependencies
- **WHEN** a plan runs for `.github`, whose dependency graph lists nothing
- **THEN** it shows no Dependabot label on `.github`

#### Scenario: A repository names an ecosystem that isn't declared
- **WHEN** a repository's label set names a Dependabot ecosystem that the Dependabot set doesn't declare
- **THEN** `scripts/check.py` fails, naming the repository and the ecosystem

#### Scenario: A Dependabot label's description over GitHub's limit
- **WHEN** a declared Dependabot label's description is longer than 100 characters
- **THEN** `scripts/check.py` fails, naming the label and its length
