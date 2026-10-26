## ADDED Requirements

### Requirement: A review run names each permission denial in its log
When Claude is refused a tool call, the review run SHALL name the call in its log as a warning: the tool and its
input, cut short. The run SHALL show nothing else from the session, which stays hidden. A run with no denial SHALL say
so. Reporting SHALL use no secret, and SHALL NOT fail the run or stop the review's comments from being posted.

#### Scenario: A call is refused
- **WHEN** Claude tries a tool its list doesn't allow, such as fetching a URL
- **THEN** the run shows a warning naming that tool and its input, and the review's comments are still posted

#### Scenario: Nothing is refused
- **WHEN** a review finishes without a denial
- **THEN** the run's log says no call was refused, and shows no warning for it

#### Scenario: A denied input holds a workflow command
- **WHEN** a denied call's input holds a newline or `::`, for example text a pull request asked Claude to run
- **THEN** it's printed inside the one warning, and no workflow command runs from it

#### Scenario: The session's output stays hidden
- **WHEN** a review run's log is read
- **THEN** it shows the denials and the action's own summary, but not the session's messages or tool results

#### Scenario: The report is widened or dropped
- **WHEN** a change adds a step that runs another command, changes the reporting step, or gives the action
  `show_full_output` or `display_report`
- **THEN** `scripts/check.py` fails, naming the step or input

### Requirement: The review reads the org's contributing guide from its checkout
A review run SHALL check out troupe-run/.github's `CONTRIBUTING.md` into a path inside its workspace, keeping no
credential, and the prompt SHALL name that path. The review SHALL read the guide with its Read tool and gain no tool
to fetch a URL. In infrastructure, which holds the guide's source, the prompt SHALL also name that source.

#### Scenario: The review checks the guide
- **WHEN** a pull request is reviewed in troupe, infrastructure or website
- **THEN** Claude reads the guide from the checkout, and no call to fetch it is refused

#### Scenario: A pull request changes the guide's source
- **WHEN** a pull request in infrastructure changes `org-profile/CONTRIBUTING.md`
- **THEN** the prompt tells Claude that file is the guide's source, and the copy from troupe-run/.github is the
  version on its main

#### Scenario: The guide's checkout keeps a credential or leaves the workspace
- **WHEN** a change lets the guide's checkout keep its token, moves it outside the workspace, checks out another
  repository, or adds a tool that fetches URLs
- **THEN** `scripts/check.py` fails, naming what changed
