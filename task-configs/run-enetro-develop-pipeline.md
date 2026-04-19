# Run Enetro Develop Pipeline

**Ticket**: JIRA-4328

## What it does
Automatically triggers the develop pipeline on Bitbucket for the enetro-product repository.

## How to run it

### Via MCP (Claude Code)
```
run_task(activation_yaml="task_config: run-enetro-develop-pipeline\nvariables: {}")
```

### Via CLI
```bash
uv run devops-agent run task-configs/run-enetro-develop-pipeline.yaml
```

## Prerequisites
- Must be authenticated to Bitbucket: `uv run devops-agent init`
- Requires access to https://bitbucket.org/enetro-ai/enetro-product

## Steps
1. Navigate to the Bitbucket pipelines page
2. Wait for the pipeline list to load
3. Find and click the "develop" branch link
4. Click the "Run" or "Trigger" button to start the pipeline
5. Confirm pipeline has started

## Selectors used
- Pipelines page: `https://bitbucket.org/enetro-ai/enetro-product/pipelines`
- Develop link detection: JavaScript text matching for "develop" (case-insensitive)
- Run button detection: JavaScript text matching for "run" or "trigger"

## Notes
- Uses JavaScript evaluation for robust element detection since Bitbucket's UI is React-based
- Includes debug screenshots at key points for troubleshooting
- Retry-safe: uses text content matching instead of fragile CSS selectors

## Original prompt
User asked to generate task config for running develop pipeline for https://bitbucket.org/enetro-ai/enetro-product/src/main/
