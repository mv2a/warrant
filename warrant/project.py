"""A loaded project: configuration, intent, checks and ledger, and the baseline they form."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from warrant.checks import Check, load_checks
from warrant.config import CONFIG_NAME, Config, load_config
from warrant.errors import WarrantError
from warrant.hashing import digest_json
from warrant.intent import Intent, parse_intent
from warrant.ledger import Ledger


@dataclass
class Project:
    config: Config
    intent: Intent
    checks: list[Check]
    ledger: Ledger

    def baseline(self) -> dict:
        """Everything the principal approves: the intent, each check, and the gate policy."""
        return {
            "intent": self.intent.digest,
            "checks": {check.id: check.digest for check in self.checks},
            "policy": self.config.policy_digest(),
        }

    def baseline_digest(self) -> str:
        return digest_json(self.baseline())

    def approval_state(self) -> tuple[str, dict | None]:
        """("missing" | "stale" | "current", the latest approval entry). Only the latest approval counts."""
        approval = next((e for e in reversed(self.ledger.entries()) if e["type"] == "approve"), None)
        if approval is None:
            return "missing", None
        if approval["data"]["baseline"] != self.baseline_digest():
            return "stale", approval
        return "current", approval

    def changes_since(self, approval: dict) -> list[str]:
        approved, current = approval["data"], self.baseline()
        changes = []
        if approved["intent"] != current["intent"]:
            changes.append(f"{self.intent.path.name} changed")
        for check_id in sorted(set(approved["checks"]) | set(current["checks"])):
            before, after = approved["checks"].get(check_id), current["checks"].get(check_id)
            if before is None:
                changes.append(f"check {check_id} was added")
            elif after is None:
                changes.append(f"check {check_id} was removed")
            elif before != after:
                changes.append(f"check {check_id} changed")
        if approved["policy"] != current["policy"]:
            changes.append("the gate policy changed")
        return changes

    def coverage(self) -> dict[str, list[Check]]:
        return {clause.id: [c for c in self.checks if clause.id in c.covers] for clause in self.intent.clauses}

    def incidents(self) -> list[dict]:
        return [
            {**entry["data"], "time": entry["time"], "seq": entry["seq"]}
            for entry in self.ledger.entries()
            if entry["type"] == "incident"
        ]


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    raise WarrantError(f"no {CONFIG_NAME} in {start} or any directory above it; run 'warrant init' first")


def load_project(root: Path) -> Project:
    config = load_config(root)
    intent = parse_intent(config.intent_path)
    return Project(config, intent, load_checks(config, intent), Ledger(config.ledger_dir))
