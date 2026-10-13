"""What the guard's hook grants: plain gh reads and everyday writes, only from the reviewed guard
(spec: development-workflow; guard-grants-gh design D1-D4)."""

import guard

# What is granted (D1)


def test_every_granted_command_is_on_the_allow_list() -> None:
    assert guard.GH_GRANTED <= guard.GH_READS | guard.GH_WORKFLOW_WRITES


def test_merging_checking_out_and_running_workflows_are_not_granted() -> None:
    not_granted = {
        ("pr", "merge"),
        ("pr", "checkout"),
        ("workflow", "run"),
        ("run", "rerun"),
        ("run", "cancel"),
    }
    assert guard.GH_GRANTED & not_granted == set()


def test_the_everyday_housekeeping_writes_are_granted() -> None:
    assert {("pr", "ready"), ("issue", "edit"), ("issue", "comment")} <= guard.GH_GRANTED
