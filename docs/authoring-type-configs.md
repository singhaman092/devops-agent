# Authoring Task Configs

Task configs define reusable, composable DevOps workflows from step primitives.

## File Location

Place task config files in `~/.devops-agent/task-configs/` as `.yaml` files.

## Structure

```yaml
name: deploy-hotfix              # Unique identifier
description: "Deploy a hotfix"   # Human-readable purpose

references:                      # Link to global configs
  repo: my-service               # Key from repos.yaml
  env: staging                   # Key from environments.yaml

merge_detection:                 # Optional, overrides global
  mode: poll
  interval_seconds: 60
  timeout_seconds: 3600

notifications:                   # Per-event channel routing
  task_started: [dev-deploys]
  task_blocked: [dev-deploys, team-alerts]
  task_complete: [dev-deploys]

steps:                           # Ordered step sequence
  - step: shell.run
    name: "Clone repo"           # Optional human label
    params:
      command: "git clone ${clone_url}"
```

## Variables

Steps use `${var}` syntax. Variables come from:
1. **Activation file** — per-run values the dev provides
2. **Step outputs** — accumulated from prior steps (e.g., `${pr_url}`, `${clone_dir}`)
3. **Global config** — available implicitly

## Step Composition Patterns

### Clone + Branch + Change + PR
```yaml
steps:
  - step: git.clone
    params: { url: "${clone_url}" }
  - step: git.branch
    params: { branch: "feature/${branch_suffix}", cwd: "${clone_dir}" }
  - step: shell.run
    params: { command: "${change_command}", cwd: "${clone_dir}" }
  - step: git.commit
    params: { message: "${commit_message}", cwd: "${clone_dir}" }
  - step: git.push
    params: { branch: "feature/${branch_suffix}", cwd: "${clone_dir}" }
  - step: pr.create
    params:
      title: "${pr_title}"
      source_branch: "feature/${branch_suffix}"
```

### PR + Wait + Deploy + Verify
```yaml
steps:
  - step: pr.wait_merge
    params: { mode: poll }
  - step: deploy.trigger
    params:
      click_selectors: ["[data-testid='deploy-btn']"]
  - step: monitor.http_check
    params:
      url: "https://staging.example.com/health"
      timeout_seconds: 300
  - step: notify.send
    params:
      channel: dev-deploys
      template: deploy_succeeded
```

## Failure Behavior

All steps default to `pause_and_notify` on failure:
1. Task moves to `waiting/`
2. Dev gets notified via configured channels
3. Dev can `resume` (retries the failed step) or `cancel`

## Validation

Always validate before deploying:

```bash
devops-agent validate ~/.devops-agent/task-configs/my-task.yaml
```

## Tips

- Keep task configs focused — one workflow per file
- Use variables for anything that changes between runs
- Reference `docs/step-primitives.md` for all available params
- The `${clone_dir}` output from `git.clone` is useful as `cwd` for subsequent steps
- `notify.send` failures never block the task — notifications are best-effort
