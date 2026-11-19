# Proposal

## Why

The 0.2.0 milestone's description, which troupe.run's `/status/` shows under Releases once 0.2.0 is out, no longer says
what 0.2.0 delivers (#335, found by troupe-run/troupe#425):

- the OpenAI runner serves OpenAI's Responses API and services that serve it, not "any OpenAI-style API";
- it leaves out the Anthropic runner (Claude's Messages API, or a local engine that serves it);
- mistral.rs runs in the runner's own process, with no API;
- it doesn't mention `troupe init`, which sets up a theatre and auditions an actor.

It should be right before troupe's 0.2.0 release pull request (troupe-run/troupe#263) merges.

## What Changes

- The description of the milestone titled 0.2.0 (key `0.14.0` in `tofu/milestones.json`) becomes: "Other runners: an
  actor runs without Claude Code, on OpenAI’s Responses API, Claude’s Messages API, a local model through Ollama or
  mistral.rs, or an engine that serves either API; troupe init auditions one". It uses typographic apostrophes, as
  the milestones spec requires.

## Capabilities

### New Capabilities

### Modified Capabilities

None: this changes declared data, not a requirement (`skip_specs: true`).

## Impact

- `tofu/milestones.json`. The plan changes that milestone's description in place, in every repository the milestones
  are declared for, and nothing else.
