"""The capability-label rule: a troupe spec's Capability: line, checked on GitHub against the
labels troupe-run/infrastructure declares on main (guard-capability-label-at-proposal)."""

import pytest

import guard


def spec(first_line: str) -> str:
    return f"# x Specification\n\n## Purpose\n\n{first_line}\n\nWhat x is for.\n\n## Requirements\n"


# Design D6: the line's one reading, now in the delivered guard.


@pytest.mark.parametrize(
    ("spec_md", "labels"),
    [
        (spec("Capability: `cap:stages`"), ["cap:stages"]),
        (spec("Capability: `cap:stages`, `cap:vcs`"), ["cap:stages", "cap:vcs"]),
        ("# x\n\n## Requirements\n\nCapability: `cap:stages`\n", []),
        (spec("Defines where a run works, as `cap:stages` says."), []),
    ],
    ids=["one", "two", "no-purpose", "prose-first"],
)
def test_capability_labels_reads_the_labels_the_line_names(spec_md: str, labels: list[str]) -> None:
    assert guard.capability_labels(spec_md) == labels


@pytest.mark.parametrize(
    "line",
    [
        "Capabilities: `cap:stages`",
        "capability: `cap:stages`",
        "Capability:",
        "Capability: cap:stages",
        "Capability: `cap:vcs`, `cap:vcs`",
        "Capability: `cap:vcs` (and git)",
    ],
    ids=["plural", "lower-case", "empty", "no-backticks", "repeated", "trailing-prose"],
)
def test_capability_labels_refuses_a_malformed_line_rather_than_reading_part_of_it(
    line: str,
) -> None:
    with pytest.raises(guard.MalformedCapabilityLineError) as raised:
        guard.capability_labels(spec(line))
    assert str(raised.value) == line
