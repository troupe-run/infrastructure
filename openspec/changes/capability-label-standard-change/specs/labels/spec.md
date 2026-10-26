# Spec Delta

## ADDED Requirements

### Requirement: A new capability label is a standard change
A new troupe capability label SHALL be added by the standard steps written once in this repository, from a
sub-issue that carries them as its checklist, so each label goes through the same steps. They SHALL leave to the
owner only approving the pull request's plan, merging it, approving the apply, and adding the board's option.

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

#### Scenario: After the apply
- **WHEN** the apply has created `cap:workspaces`
- **THEN** troupe-run/troupe#42 gets the label with its other labels unchanged, the board's `Capability` field gets
  the option, and the sub-issue is closed with its card Done and a comment naming the pull request and the change

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
