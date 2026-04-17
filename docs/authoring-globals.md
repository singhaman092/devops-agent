# Authoring Global Configs (Platform Eng)

Global configs live in `~/.devops-agent/` and are typically authored by platform engineering, then shared across the team via git.

On Windows, `~` resolves to `C:\Users\<username>`, so the full path is:

```
C:\Users\<username>\.devops-agent\
    config.yaml
    repos.yaml
    environments.yaml
    notifications.yaml
    task-configs\
        deploy-new-env.yaml
        hotfix.yaml
        ...
```

Run `devops-agent init` to create this directory structure automatically.

## Files

| File | Location | Who authors |
|------|----------|-------------|
| `config.yaml` | `~/.devops-agent/config.yaml` | Platform eng |
| `repos.yaml` | `~/.devops-agent/repos.yaml` | Platform eng |
| `environments.yaml` | `~/.devops-agent/environments.yaml` | Platform eng |
| `notifications.yaml` | `~/.devops-agent/notifications.yaml` | Platform eng |
| Task configs | `~/.devops-agent/task-configs/*.yaml` | Devs |

## config.yaml

```yaml
work_dir: "~/.devops-agent/work"
edge_profile_dir: "~/.devops-agent/edge-profile"
default_merge_detection: poll
poll_interval_seconds: 60
poll_timeout_seconds: 3600
default_notification_channels:
  - dev-deploys
log_level: INFO
log_json: true
login_targets:
  - "https://login.microsoftonline.com"
  - "https://dev.azure.com"
  - "https://app.slack.com"
```

`login_targets` are URLs that the dev must authenticate against during `devops-agent init`. The agent opens each in Edge and waits for the dev to log in.

## repos.yaml

```yaml
repos:
  my-service:
    clone_url: "https://dev.azure.com/org/project/_git/my-service"
    platform: azure_devops        # azure_devops | github | gitlab
    pr_create_url_template: "https://dev.azure.com/org/project/_git/my-service/pullrequestcreate?sourceRef=${branch_name}"
    pr_view_url_template: "https://dev.azure.com/org/project/_git/my-service/pullrequest/${pr_id}"
    pr_template_path: ".azuredevops/pull_request_template.md"
    title_convention: "^(feat|fix|chore)\\(.*\\): .+"
    default_reviewers:
      - "team-lead@example.com"
    required_labels:
      - "auto-deploy"
```

The `platform` field determines which PR page filler is used. Each platform has its own selectors for filling the PR form.

## environments.yaml

```yaml
environments:
  staging:
    deploy_portal_url: "https://portal.azure.com/#resource/my-staging-app"
    deploy_trigger: portal_click   # portal_click | pipeline_url | cli
    required_params:
      version: "Git SHA or tag to deploy"
    health_checks:
      - url: "https://staging.example.com/health"
        expected_status: 200
        expected_body: "ok"
        timeout_seconds: 300
    monitor_timeout_seconds: 600
    repos:
      - my-service
```

`deploy_trigger` types:
- **portal_click** — Agent navigates to portal URL and clicks a sequence of selectors
- **pipeline_url** — Agent navigates to a CI/CD pipeline URL and triggers a run
- **cli** — Agent runs a shell command to trigger deploy

## notifications.yaml

```yaml
channels:
  dev-deploys:
    url: "https://app.slack.com/client/T12345/C12345"
    platform: slack
  team-alerts:
    url: "https://teams.microsoft.com/l/channel/19%3Axyz/General"
    platform: teams

templates:
  task_started: "Task ${task_id} started: ${task_config_name}"
  task_blocked: "Task ${task_id} blocked at step '${failed_step}': ${error_message}"
  task_complete: "Task ${task_id} completed successfully"
  pr_created: "PR created: ${pr_url}"
  deploy_triggered: "Deploy triggered for ${env}"
  deploy_succeeded: "Deploy to ${env} succeeded"
```

Templates use `${var}` placeholders. Available variables include: `task_id`, `task_config_name`, `repo`, `env`, `pr_url`, `deployed_version`, `error_message`, `failed_step`, `duration`.

## Sharing Across the Team

Keep globals in a git repo and have devs clone/pull into `~/.devops-agent/`:

```bash
git clone https://internal/devops-agent-configs ~/.devops-agent
```

Task configs (`task-configs/`) can live alongside globals or in separate repos.
