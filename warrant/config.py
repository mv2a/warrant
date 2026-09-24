"""warrant.toml: where things live, and which evidence authorizes which action."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from warrant.errors import WarrantError
from warrant.hashing import digest_json

CONFIG_NAME = "warrant.toml"
STRENGTHS = ("judged", "tested", "proved")

_TOP_LEVEL = {"project", "checks", "gates"}
_PROJECT_FIELDS = {"name", "intent", "workspace", "ledger"}
_CHECKS_FIELDS = {"public", "holdout"}
_GATE_FIELDS = {"checks", "min_strength", "after", "cover_all_intent", "require_regressions"}


@dataclass
class Gate:
    name: str
    checks: list[str]
    min_strength: str
    after: list[str]
    cover_all_intent: bool
    require_regressions: bool

    def policy(self) -> dict:
        return {
            "checks": self.checks,
            "min_strength": self.min_strength,
            "after": self.after,
            "cover_all_intent": self.cover_all_intent,
            "require_regressions": self.require_regressions,
        }


@dataclass
class Config:
    root: Path
    name: str
    intent_path: Path
    workspace: Path | None
    ledger_dir: Path
    public_dir: Path | None
    holdout_dir: Path | None
    gates: dict[str, Gate]

    def policy_digest(self) -> str:
        return digest_json({name: gate.policy() for name, gate in sorted(self.gates.items())})

    def display(self, path: Path) -> str:
        """A path as people should see it: relative to the project when possible."""
        return os.path.relpath(path.resolve(), self.root)

    def separation_problems(self, workspace: Path) -> list[str]:
        """Ways the builder working in this workspace could read what it must not."""
        workspace = workspace.resolve()
        problems = []
        for label, path in (("the hidden checks", self.holdout_dir), ("the ledger", self.ledger_dir)):
            if path is not None and path.resolve().is_relative_to(workspace):
                problems.append(
                    f"{label} ({self.display(path)}) would be inside the builder's workspace "
                    f"({self.display(workspace)}), where the builder could read them"
                )
        return problems


def load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise WarrantError(f"file not found: {path}") from None
    except tomllib.TOMLDecodeError as error:
        raise WarrantError(f"{path}: {error}") from None


def load_config(root: Path) -> Config:
    root = root.resolve()
    data = load_toml(root / CONFIG_NAME)
    _known(data, _TOP_LEVEL, CONFIG_NAME)
    project = _table(data, "project", CONFIG_NAME)
    checks = _table(data, "checks", CONFIG_NAME)
    gate_tables = _table(data, "gates", CONFIG_NAME)
    _known(project, _PROJECT_FIELDS, "[project]")
    _known(checks, _CHECKS_FIELDS, "[checks]")
    if not gate_tables:
        raise WarrantError(f"{CONFIG_NAME} defines no gates; add one such as [gates.merge]")
    gates = {name: _gate(name, table) for name, table in gate_tables.items()}
    _check_order(gates)
    public, holdout = _path(root, checks, "public", "[checks]"), _path(root, checks, "holdout", "[checks]")
    if public is None and holdout is None:
        raise WarrantError("[checks] needs a public or a holdout directory")
    return Config(
        root=root,
        name=_string(project, "name", "[project]", default=root.name),
        intent_path=_path(root, project, "intent", "[project]", default="intent.md"),
        workspace=_path(root, project, "workspace", "[project]"),
        ledger_dir=_path(root, project, "ledger", "[project]", default="ledger"),
        public_dir=public,
        holdout_dir=holdout,
        gates=gates,
    )


def validate_selector(selector: str, where: str) -> None:
    if selector in ("all", "public", "holdout"):
        return
    kind, separator, value = selector.partition(":")
    if separator and kind in ("tag", "id") and value:
        return
    raise WarrantError(f"{where}: unknown check selector {selector!r}; use all, public, holdout, tag:NAME or id:ID")


def _gate(name: str, table) -> Gate:
    where = f"[gates.{name}]"
    if not isinstance(table, dict):
        raise WarrantError(f"{where} must be a table")
    _known(table, _GATE_FIELDS, where)
    selectors = _strings(table, "checks", where, default=["all"])
    for selector in selectors:
        validate_selector(selector, where)
    strength = table.get("min_strength", "tested")
    if strength not in STRENGTHS:
        raise WarrantError(f"{where}: min_strength must be one of {', '.join(STRENGTHS)}")
    return Gate(
        name=name,
        checks=selectors,
        min_strength=strength,
        after=_strings(table, "after", where, default=[]),
        cover_all_intent=_bool(table, "cover_all_intent", where),
        require_regressions=_bool(table, "require_regressions", where),
    )


def _check_order(gates: dict[str, Gate]) -> None:
    for gate in gates.values():
        for prerequisite in gate.after:
            if prerequisite not in gates:
                raise WarrantError(f"[gates.{gate.name}] comes after {prerequisite!r}, which is not a gate")

    def visit(name: str, path: tuple[str, ...]) -> None:
        if name in path:
            raise WarrantError("gates depend on each other in a loop: " + " -> ".join((*path, name)))
        for prerequisite in gates[name].after:
            visit(prerequisite, (*path, name))

    for name in gates:
        visit(name, ())


def _known(table: dict, allowed: set[str], where: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise WarrantError(f"{where}: unknown setting(s) {', '.join(unknown)}")


def _table(data: dict, key: str, where: str) -> dict:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise WarrantError(f"{where}: [{key}] must be a table")
    return value


def _string(table: dict, key: str, where: str, default: str | None = None) -> str | None:
    value = table.get(key, default)
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise WarrantError(f"{where}: {key} must be a non-empty string")
    return value


def _strings(table: dict, key: str, where: str, default: list[str]) -> list[str]:
    value = table.get(key, default)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise WarrantError(f"{where}: {key} must be a list of strings")
    return value


def _bool(table: dict, key: str, where: str) -> bool:
    value = table.get(key, False)
    if not isinstance(value, bool):
        raise WarrantError(f"{where}: {key} must be true or false")
    return value


def _path(root: Path, table: dict, key: str, where: str, default: str | None = None) -> Path | None:
    value = _string(table, key, where, default)
    return None if value is None else (root / value).resolve()
