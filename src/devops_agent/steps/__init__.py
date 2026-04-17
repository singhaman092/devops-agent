"""Step primitives package — importing this module registers all built-in steps."""

# Import all step modules to trigger @register_step decorators
from devops_agent.steps import (  # noqa: F401
    browser_click,
    browser_eval,
    browser_fill,
    browser_keys,
    browser_navigate,
    browser_screenshot,
    browser_wait_for,
    deploy_trigger,
    git,
    monitor_http,
    monitor_version,
    notify,
    ocr_find,
    os_click,
    os_type,
    pr_create,
    pr_wait_merge,
    screenshot,
    shell,
    wait,
)
