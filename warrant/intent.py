"""Intent documents: Markdown in which every promise is a list item that starts with an ID."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from warrant.errors import WarrantError
from warrant.hashing import digest_bytes

CLAUSE = re.compile(r"^[-*] +([A-Z]{1,3}[0-9]{1,4}): +(\S.*)$")
INFORMATIONAL_SECTIONS = ("out of scope", "non-goals", "non goals")


@dataclass
class Clause:
    id: str
    text: str
    section: str
    line: int


@dataclass
class Intent:
    path: Path
    title: str
    meta: dict[str, str]
    clauses: list[Clause]
    digest: str

    @property
    def ids(self) -> list[str]:
        return [clause.id for clause in self.clauses]

    def clause(self, clause_id: str) -> Clause | None:
        return next((clause for clause in self.clauses if clause.id == clause_id), None)


def parse_intent(path: Path) -> Intent:
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise WarrantError(f"intent file not found: {path}") from None
    lines = raw.decode("utf-8").split("\n")
    meta, start = _front_matter(lines, path)
    title = meta.get("title", "")
    section = ""
    clauses: list[Clause] = []
    defined_on: dict[str, int] = {}
    current: Clause | None = None
    fenced = False
    for number, line in enumerate(lines[start:], start=start + 1):
        line = line.rstrip("\r")
        if line.lstrip().startswith(("```", "~~~")):
            fenced, current = not fenced, None
            continue
        if fenced:
            continue
        if line.startswith("#"):
            current = None
            level = len(line) - len(line.lstrip("#"))
            heading = line[level:].strip()
            if level == 1 and not title:
                title = heading
            elif level == 2:
                section = heading
            continue
        match = CLAUSE.match(line)
        if match:
            current = None
            if section.lower().startswith(INFORMATIONAL_SECTIONS):
                continue
            clause_id, text = match.groups()
            if clause_id in defined_on:
                raise WarrantError(
                    f"{path.name}:{number}: clause {clause_id} is already defined on line {defined_on[clause_id]}"
                )
            defined_on[clause_id] = number
            current = Clause(clause_id, text.strip(), section, number)
            clauses.append(current)
        elif current is not None and line[:1] in (" ", "\t") and line.strip():
            current.text += " " + line.strip()
        else:
            current = None
    if not clauses:
        raise WarrantError(
            f"{path.name} has no promises. Write each one as a list item that starts with an ID, like '- G1: ...'"
        )
    return Intent(path, title or path.stem, meta, clauses, digest_bytes(raw))


def _front_matter(lines: list[str], path: Path) -> tuple[dict[str, str], int]:
    if not lines or lines[0].strip() != "---":
        return {}, 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            meta = {}
            for entry in lines[1:index]:
                key, separator, value = entry.partition(":")
                if separator and key.strip():
                    meta[key.strip()] = value.strip()
            return meta, index + 1
    raise WarrantError(f"{path.name}: front matter opens with '---' but never closes")
