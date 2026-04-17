"""Install Playwright browsers (Edge/Chromium) for the agent."""

import subprocess
import sys


def main() -> None:
    print("Installing Playwright browsers...")
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )
    print("Done. Chromium/Edge driver installed.")


if __name__ == "__main__":
    main()
