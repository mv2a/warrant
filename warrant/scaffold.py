"""Starter files for 'warrant init'."""

from __future__ import annotations

from pathlib import Path

from warrant.config import CONFIG_NAME
from warrant.errors import WarrantError

CONFIG = """\
# Warrant: humans state intent, agents write the code, evidence decides what ships.
# Format: https://github.com/mv2a/warrant/blob/main/SPEC.md

[project]
name = "{name}"
intent = "intent.md"
# The builder's code. Give builders access to this directory and nothing else.
workspace = "workspace"
ledger = "ledger"

[checks]
public = "checks/public"    # builders may read these
holdout = "checks/holdout"  # builders must never read these

# Each gate says which evidence authorizes an action.
[gates.merge]
checks = ["all"]
min_strength = "tested"
cover_all_intent = true

[gates.release]
after = ["merge"]
checks = ["all"]
min_strength = "tested"
require_regressions = true
"""

INTENT = """\
# {name}

Say who this is for and why it matters, in a few sentences.

Each promise is a list item that starts with an ID. A gate with cover_all_intent
issues no warrant until every promise has at least one check.

## Goals

- G1: Replace this with an outcome you want, stated so that someone could check it.

## Constraints

- C1: Replace this with a rule the software must never break.

## Scenarios

- S1: Replace this with a concrete example: given this input, the result is exactly that.

## Out of scope

- Things you are deliberately not asking for. Items here are not promises.
"""

PUBLIC_CHECKS = """\
# Visible checks: builders may read and run these.
# A check passes when its command exits with status 0. The command runs in a copy
# of this folder, with $WARRANT_WORKSPACE pointing to a copy of the workspace.

[[check]]
id = "P1"
covers = ["S1"]
statement = "Replace with a plain-language description of what this check shows."
strength = "tested"
run = ["python3", "check_scenarios.py"]
"""

HOLDOUT_CHECKS = """\
# Hidden checks: builders must never see these. For real work, keep this folder
# somewhere builders can't read, such as a separate private repository.

[[check]]
id = "H1"
covers = ["G1", "C1"]
statement = "Replace with a plain-language description of what this check shows."
strength = "tested"
run = ["python3", "check_goals.py"]
"""

PLACEHOLDER = """\
import sys

sys.exit("This is a placeholder. Replace it with a real check.")
"""


def create(target: Path, name: str) -> list[Path]:
    files = {
        CONFIG_NAME: CONFIG.format(name=name.replace("\\", "\\\\").replace('"', '\\"')),
        "intent.md": INTENT.format(name=name),
        "checks/public/checks.toml": PUBLIC_CHECKS,
        "checks/public/check_scenarios.py": PLACEHOLDER,
        "checks/holdout/checks.toml": HOLDOUT_CHECKS,
        "checks/holdout/check_goals.py": PLACEHOLDER,
    }
    existing = [relative for relative in files if (target / relative).exists()]
    if existing:
        raise WarrantError(f"{target} already has {', '.join(existing)}")
    for relative, text in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (target / "workspace").mkdir(exist_ok=True)
    return [target / relative for relative in files]
