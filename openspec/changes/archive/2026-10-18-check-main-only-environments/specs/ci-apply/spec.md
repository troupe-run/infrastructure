## MODIFIED Requirements

### Requirement: Only main can apply
An apply SHALL run only on `main`, after the owner's approval. The credential that can change the org SHALL reach a
workflow run only when the run is on `main` or the owner has approved it. A run on any other branch SHALL NOT reach
the environments that `main` uses.

#### Scenario: A branch can't apply
- **WHEN** a workflow run on a branch other than `main` asks for the apply environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from that environment

#### Scenario: Removing or weakening main's environments fails the check
- **WHEN** a change deletes the declaration of the environment that plans `main` or the apply environment, lets
  either deploy from a branch other than `main`, lets admins bypass either, or removes the owner as the apply
  environment's required reviewer
- **THEN** `scripts/check.py` fails, naming the environment and what changed, before any plan is made
