"""Template rendering for notifications."""

from __future__ import annotations

import re


def render_template(template: str, variables: dict[str, str]) -> str:
    """Render a template string by substituting ${var} placeholders."""

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return re.sub(r"\$\{(\w+)\}", replacer, template)
