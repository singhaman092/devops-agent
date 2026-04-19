# run-enetro-develop-pipeline

## What it does
Manually triggers the `branches: develop` pipeline on the `develop` branch of the `enetro-product` Bitbucket repo. This deploys to the **ECS dev env (Enetro)**.

## Ticket
JIRA-4444

## How to run

### CLI
```bash
uv run devops-agent run --task-config run-enetro-develop-pipeline
```

### MCP (via AI assistant)
```
run_task("task_config: run-enetro-develop-pipeline\nvariables: {}")
```

## Variables
None required.

## Original prompt
> "run devops-agent and configure repo https://bitbucket.org/enetro-ai/enetro-product/src/main/ to run develop pipeline"

## Notes
- The Bitbucket "Run Pipeline" dialog has two dropdowns: Branch and Pipeline type.
- Branch is a react-select (testid: `branch-selector-select--select--input`) — typed via native value setter + input event dispatch.
- Pipeline dropdown (id: `react-select-run-pipeline-selector-select-input`) is opened via `mousedown` on the control div.
- The `branches: develop` option deploys to ECS dev env. Available options on develop branch: `branches: beta`, `branches: develop`, `branches: main`.
- The Run button (`data-testid="run-pipeline"`) must be clicked via `browser.click` (JS `.click()` alone does not submit the form).
