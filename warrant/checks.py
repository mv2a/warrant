"""Checks: the machine-decidable form of the intent, approved by a principal."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from warrant.config import STRENGTHS, Config, load_toml
from warrant.errors import WarrantError
from warrant.hashing import digest_json, tree_digest
from warrant.intent import Intent

MANIFEST = "checks.toml"
_FIELDS = {"id", "covers", "statement", "run", "strength", "timeout", "tags", "regression_for"}
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


@dataclass
class Check:
    id: str
    visibility: str  # "public" (the builder may see it) or "holdout" (the builder must not)
    covers: list[str]
    statement: str
    run: list[str]
    strength: str
    timeout: int
    tags: list[str]
    regression_for: list[str]
    directory: Path
    digest: str  # covers the definition and every file in the check's directory

    def matches(self, selector: str) -> bool:
        if selector == "all":
            return True
        if selector in ("public", "holdout"):
            return self.visibility == selector
        kind, _, value = selector.partition(":")
        return (kind == "tag" and value in self.tags) or (kind == "id" and value == self.id)


def load_checks(config: Config, intent: Intent) -> list[Check]:
    checks: list[Check] = []
    seen: set[str] = set()
    for visibility, directory in (("public", config.public_dir), ("holdout", config.holdout_dir)):
        if directory is None:
            continue
        manifest = directory / MANIFEST
        if not manifest.is_file():
            raise WarrantError(f"missing {config.display(manifest)}")
        entries = load_toml(manifest).get("check", [])
        if not isinstance(entries, list):
            raise WarrantError(f"{config.display(manifest)}: write checks as [[check]] tables")
        files = tree_digest(directory)
        for number, entry in enumerate(entries, start=1):
            check = _parse(entry, visibility, directory, files, intent, f"{config.display(manifest)}, check {number}")
            if check.id in seen:
                raise WarrantError(f"check {check.id} is defined more than once")
            seen.add(check.id)
            checks.append(check)
    return checks


def _parse(entry, visibility: str, directory: Path, files: str, intent: Intent, where: str) -> Check:
    if not isinstance(entry, dict):
        raise WarrantError(f"{where}: each [[check]] must be a table")
    unknown = sorted(set(entry) - _FIELDS)
    if unknown:
        raise WarrantError(f"{where}: unknown field(s) {', '.join(unknown)}")
    check_id = entry.get("id")
    if not isinstance(check_id, str) or not _ID.match(check_id):
        raise WarrantError(f"{where}: id must be a short identifier such as P1 or H3")
    where = f"check {check_id}"

    covers = entry.get("covers")
    if not isinstance(covers, list) or not covers or not all(isinstance(c, str) for c in covers):
        raise WarrantError(f'{where}: covers must list the promises it checks, e.g. covers = ["G1"]')
    missing = [clause for clause in covers if intent.clause(clause) is None]
    if missing:
        raise WarrantError(f"{where} covers {', '.join(missing)}, which {intent.path.name} does not define")

    statement = entry.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        raise WarrantError(f"{where}: statement must say in plain words what the check shows")

    run = entry.get("run")
    if isinstance(run, str):
        run = shlex.split(run)
    if not isinstance(run, list) or not run or not all(isinstance(part, str) for part in run):
        raise WarrantError(f"{where}: run must be a command, as a string or a list of strings")

    strength = entry.get("strength")
    if strength not in STRENGTHS:
        raise WarrantError(f"{where}: strength must be one of {', '.join(STRENGTHS)}")

    timeout = entry.get("timeout", 120)
    if type(timeout) is not int or timeout <= 0:
        raise WarrantError(f"{where}: timeout must be a whole number of seconds")

    definition = {
        "id": check_id,
        "visibility": visibility,
        "covers": covers,
        "statement": " ".join(statement.split()),
        "run": run,
        "strength": strength,
        "timeout": timeout,
        "tags": _strings(entry, "tags", where),
        "regression_for": _strings(entry, "regression_for", where),
    }
    digest = digest_json({"definition": definition, "files": files})
    return Check(**definition, directory=directory, digest=digest)


def _strings(entry: dict, key: str, where: str) -> list[str]:
    value = entry.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise WarrantError(f"{where}: {key} must be a list of strings")
    return value
