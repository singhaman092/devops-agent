# Step Primitives Reference

Each step primitive has a stable name used in task-config YAML files. Parameters are validated at load time.

## Shell & Git

### `shell.run`
Execute a command via Git Bash.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | yes | Shell command to execute |
| `cwd` | string | no | Working directory (default: task work_dir) |
| `timeout` | int | no | Timeout in seconds (default: 300) |

**Outputs:** `exit_code`, `stdout`

### `git.clone`
Clone a repository.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | Git clone URL |
| `dest` | string | no | Destination directory (default: work_dir/repo) |

**Outputs:** `clone_dir`

### `git.branch`
Create and checkout a new branch.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `branch` | string | yes | Branch name |
| `cwd` | string | no | Repo directory |
| `base` | string | no | Base branch to branch from (fetches from origin) |

**Outputs:** `branch_name`

### `git.commit`
Stage and commit changes.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | yes | Commit message |
| `cwd` | string | no | Repo directory |
| `add_all` | bool | no | Run `git add -A` first (default: true) |

### `git.push`
Push to remote.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `branch` | string | no | Branch name |
| `cwd` | string | no | Repo directory |
| `remote` | string | no | Remote name (default: origin) |
| `set_upstream` | bool | no | Use -u flag (default: true) |

## Browser

### `browser.navigate`
Navigate to a URL in the Edge profile.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | URL to navigate to |
| `wait_until` | string | no | Page load strategy (default: domcontentloaded) |

**Outputs:** `url`, `title`

### `browser.click`
Click a DOM element.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `selector` | string | yes | CSS selector |
| `timeout` | int | no | Timeout in ms (default: 30000) |

### `browser.fill`
Fill an input element.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `selector` | string | yes | CSS selector |
| `value` | string | yes | Text to fill |
| `timeout` | int | no | Timeout in ms (default: 30000) |
| `clear` | bool | no | Clear field first (default: true) |

### `browser.wait_for`
Wait for a selector or text to appear.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `selector` | string | conditional | CSS selector to wait for |
| `text` | string | conditional | Text to wait for |
| `state` | string | no | visible, hidden, attached, detached (default: visible) |
| `timeout` | int | no | Timeout in ms (default: 30000) |

### `browser.screenshot`
Take a screenshot of the page or element.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | string | no | Output filename |
| `selector` | string | no | Element to capture (default: full page) |
| `full_page` | bool | no | Full page capture (default: true) |

**Outputs:** `screenshot_path`

## OS-Level

### `screenshot.capture`
OS-level screenshot via mss/pywin32.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | no | full, region, or window (default: full) |
| `filename` | string | no | Output filename |
| `region` | object | no | `{left, top, width, height}` for region mode |

**Outputs:** `screenshot_path`

### `ocr.find_text`
Find text on screen using RapidOCR.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes | Text to search for |
| `image_path` | string | no | Image to search (default: takes screenshot) |

**Outputs:** `found`, `text`, `center_x`, `center_y`, `confidence`, `bbox`

### `os.click`
Click at screen coordinates.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | int | yes | X coordinate |
| `y` | int | yes | Y coordinate |
| `button` | string | no | left, right, middle (default: left) |
| `clicks` | int | no | Number of clicks (default: 1) |

### `os.type`
Type text via keyboard.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes | Text to type |
| `interval` | float | no | Delay between keystrokes (default: 0.02) |

### `os.hotkey`
Press a key combination.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `keys` | list[string] | yes | Keys to press (e.g., ["ctrl", "s"]) |

## PR

### `pr.create`
Composite step: navigate to PR creation page, fill template, submit.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | PR title |
| `description` | string | no | PR body (auto-loads repo template if empty) |
| `source_branch` | string | no | Source branch |
| `target_branch` | string | no | Target branch (default: main) |
| `reviewers` | list | no | Override default reviewers |
| `labels` | list | no | Override required labels |

**Outputs:** `pr_url`, `pr_title`, `source_branch`, `target_branch`

### `pr.wait_merge`
Wait for a PR to be merged.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pr_url` | string | no | PR URL (default: from prior pr.create output) |
| `mode` | string | no | poll or suspend (default: from config) |
| `interval_seconds` | int | no | Poll interval |
| `timeout_seconds` | int | no | Poll timeout |

**Outputs:** `pr_url`, `merged`, `elapsed_seconds`

## Deploy & Monitor

### `deploy.trigger`
Trigger a deployment via the environment's configured method.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | no | Override deploy portal URL |
| `click_selectors` | list | no | Selectors to click (portal_click mode) |
| `pipeline_url` | string | no | Pipeline URL (pipeline_url mode) |
| `command` | string | no | Shell command (cli mode) |

**Outputs:** `deploy_url`, `trigger_type`

### `monitor.http_check`
Poll a URL for expected status/body.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | URL to check |
| `expected_status` | int | no | Expected HTTP status (default: 200) |
| `expected_body` | string | no | Expected substring in body |
| `interval_seconds` | int | no | Poll interval (default: 30) |
| `timeout_seconds` | int | no | Poll timeout (default: 300) |

**Outputs:** `status_code`, `elapsed_seconds`

### `monitor.version_match`
Poll a version endpoint until it returns the expected value.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | Version endpoint URL |
| `expected_version` | string | yes | Expected version string |
| `json_path` | string | no | Dot-separated path into JSON response (default: version) |
| `interval_seconds` | int | no | Poll interval (default: 30) |
| `timeout_seconds` | int | no | Poll timeout (default: 600) |

**Outputs:** `version`, `elapsed_seconds`

## Notifications

### `notify.send`
Post a message to Slack or Teams via browser.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `channel` | string | yes | Channel name from notifications.yaml |
| `message` | string | conditional | Message text |
| `template` | string | conditional | Template name from notifications.yaml |

**Outputs:** `channel`, `platform`

## Utility

### `wait.sleep`
Explicit delay.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `seconds` | int | no | Seconds to wait (default: 5) |

**Outputs:** `slept_seconds`
