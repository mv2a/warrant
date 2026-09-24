"""Run the workspace's `quote` command the way the contract describes."""

import json
import os
import subprocess
import sys

QUOTE = os.path.join(os.environ["WARRANT_WORKSPACE"], "quote")


def call(request=None, raw=None):
    """Send a request, or raw text, to `quote`. Returns (exit status, parsed output or None)."""
    if not os.access(QUOTE, os.X_OK):
        sys.exit("the workspace has no executable named quote")
    text = raw if raw is not None else json.dumps(request)
    done = subprocess.run([QUOTE], input=text, capture_output=True, text=True, timeout=10)
    output = done.stdout.strip()
    if not output:
        return done.returncode, None
    try:
        return done.returncode, json.loads(output)
    except json.JSONDecodeError:
        return done.returncode, output


def finish(problems, summary):
    if problems:
        shown = problems if len(problems) <= 12 else problems[:10] + [f"...and {len(problems) - 10} more"]
        print("\n".join(shown))
        sys.exit(1)
    print(summary)
