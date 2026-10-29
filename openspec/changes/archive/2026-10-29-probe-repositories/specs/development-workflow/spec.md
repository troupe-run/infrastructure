# Spec Delta

## ADDED Requirements

### Requirement: A throwaway repository is judged by the name the command writes
The guard SHALL exempt a `gh` command as a write to a throwaway repository only when the command writes out the
repository's name. A name built by the shell (a variable or a substitution) SHALL be judged as a live repository, and
its refusal SHALL say that the name is built by the shell and that writing it out lets a throwaway one go ahead. A
GraphQL mutation names no repository, so it SHALL NOT be exempt in a throwaway one.

#### Scenario: A probe named through a variable
- **WHEN** an agent runs `P=infra-probe-x; gh repo create troupe-run/$P --public`, or
  `gh api -X POST repos/troupe-run/$P/git/refs` with fields
- **THEN** the command is refused as it would be for a live repository (`owner-only`, or `gh-allow-list`), and the
  message says the repository's name is built by the shell, so it can't be judged a throwaway repository, and the fix
  says to write the name out

#### Scenario: The same command with the name written out
- **WHEN** an agent runs `gh repo create troupe-run/infra-probe-x --public`, or
  `gh api -X POST repos/troupe-run/infra-probe-x/git/refs` with fields
- **THEN** the command is allowed

#### Scenario: Another owner's name built by the shell
- **WHEN** an agent runs `gh repo create someone-else/$P --public`, whose owner is written out and isn't
  `troupe-run`, so it can't be a throwaway repository whatever `$P` holds
- **THEN** the command is refused as `owner-only` with the usual message, saying nothing about a name built by the
  shell

#### Scenario: A live repository's refusal is unchanged
- **WHEN** an agent runs `gh repo create troupe-run/my-repo --public`, a name with no shell expansion
- **THEN** the command is refused as `owner-only`, and the message says nothing about a name built by the shell

#### Scenario: A help request chained with another command
- **WHEN** an agent runs `gh repo edit --help | grep -i pull ; gh repo create troupe-run/infra-probe-x --public`
- **THEN** both commands go ahead: the first as a help request, the second as a write to a throwaway repository

#### Scenario: A GraphQL mutation on a probe
- **WHEN** an agent runs `gh api graphql` with an `updateRepository` mutation whose `repositoryId` is an
  `infra-probe-*` repository's
- **THEN** the command is refused, as an unlisted mutation, as it is for any repository
