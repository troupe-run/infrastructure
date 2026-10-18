### OpenTofu plan for c37dcfa

Plan: 3 to add, 0 to change, 0 to destroy.

Made in CI on this pull request merged onto `main` ([run](https://github.com/troupe-run/infrastructure/actions/runs/39125008437)). The apply happens after the merge, once the owner approves the plan made then.


**Modes to set after the apply:** none. Every delivered file has its source's mode.

<details><summary>Full plan</summary>

```

OpenTofu used the selected providers to generate the following execution
plan. Resource actions are indicated with the following symbols:
  + create

OpenTofu will perform the following actions:

  # github_actions_variable.board_app_client_id will be created
  + resource "github_actions_variable" "board_app_client_id" {
      + created_at    = (known after apply)
      + id            = (known after apply)
      + repository    = "website"
      + repository_id = (known after apply)
      + updated_at    = (known after apply)
      + value         = "Iv23li9xJEOLGSyYlU5G"
      + variable_name = "BOARD_APP_CLIENT_ID"
    }

  # github_repository_environment.board will be created
  + resource "github_repository_environment" "board" {
      + can_admins_bypass   = false
      + environment         = "board"
      + id                  = (known after apply)
      + prevent_self_review = false
      + repository          = "website"
      + repository_id       = (known after apply)

      + deployment_branch_policy {
          + custom_branch_policies = true
          + protected_branches     = false
        }
    }

  # github_repository_environment_deployment_policy.board_main_only will be created
  + resource "github_repository_environment_deployment_policy" "board_main_only" {
      + branch_pattern = "main"
      + environment    = "board"
      + id             = (known after apply)
      + policy_id      = (known after apply)
      + repository     = "website"
      + repository_id  = (known after apply)
    }

Plan: 3 to add, 0 to change, 0 to destroy.
```
</details>
