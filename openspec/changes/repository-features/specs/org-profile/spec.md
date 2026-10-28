## ADDED Requirements

### Requirement: Questions go to troupe's discussions
The org's issue chooser SHALL offer a link that sends a question to `troupe`'s Q&A discussions, alongside the issue
forms. The contributing guide SHALL say that questions are asked there, not in an issue. Both reach every repository
that uses the org's issue forms.

#### Scenario: Someone with a question opens a new issue
- **WHEN** someone opens a new issue in a repository that uses the org's issue forms
- **THEN** the chooser offers "Ask a question", which opens `troupe`'s Q&A discussions

#### Scenario: The guide says where questions go
- **WHEN** someone reads the org's contributing guide
- **THEN** it tells them to ask questions in `troupe`'s discussions rather than open an issue
