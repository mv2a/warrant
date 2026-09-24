"""The ledger: an append-only, hash-chained record that principals read instead of code."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from warrant.errors import WarrantError
from warrant.hashing import canonical_json, digest_bytes, digest_json, hex_part, short

GENESIS = "sha256:" + "0" * 64


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Ledger:
    def __init__(self, directory: Path):
        self.directory = directory
        self.path = directory / "ledger.jsonl"
        self.evidence_dir = directory / "evidence"

    def entries(self) -> list[dict]:
        entries = []
        for number, line in enumerate(self._lines(), start=1):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise WarrantError(f"{self.path}: entry {number} is not valid JSON ({error.msg})") from None
        return entries

    def head(self) -> str:
        lines = self._lines()
        return digest_bytes(lines[-1].encode("utf-8")) if lines else GENESIS

    def append(self, kind: str, actor: str, data: dict) -> dict:
        lines = self._lines()
        entry = {
            "seq": len(lines) + 1,
            "time": utc_now(),
            "type": kind,
            "actor": actor,
            "prev": digest_bytes(lines[-1].encode("utf-8")) if lines else GENESIS,
            "data": data,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(entry).decode("utf-8") + "\n")
        return entry

    def put_evidence(self, statement: dict) -> str:
        digest = digest_json(statement)
        path = self._evidence_path(digest)
        if not path.exists():
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            text = json.dumps(statement, indent=2, sort_keys=True, ensure_ascii=False)
            path.write_text(text + "\n", encoding="utf-8")
        return digest

    def get_evidence(self, digest: str) -> dict:
        try:
            statement = json.loads(self._evidence_path(digest).read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise WarrantError(f"evidence {short(digest)} is missing") from None
        except json.JSONDecodeError:
            raise WarrantError(f"evidence {short(digest)} is not valid JSON") from None
        if digest_json(statement) != digest:
            raise WarrantError(f"evidence {short(digest)} no longer matches its digest, so it was changed")
        return statement

    def problems(self) -> list[str]:
        """Everything that shows the ledger or its evidence was altered outside Warrant."""
        problems = []
        previous = GENESIS
        for number, line in enumerate(self._lines(), start=1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"entry {number} is not valid JSON")
                previous = digest_bytes(line.encode("utf-8"))
                continue
            if entry.get("seq") != number:
                problems.append(f"entry {number} carries sequence number {entry.get('seq')}")
            if entry.get("prev") != previous:
                problems.append(f"entry {number} does not chain to the entry before it")
            if canonical_json(entry).decode("utf-8") != line:
                problems.append(f"entry {number} is not in canonical form, so it was edited outside Warrant")
            previous = digest_bytes(line.encode("utf-8"))
            if entry.get("type") == "verify":
                for result in entry.get("data", {}).get("results", []):
                    try:
                        self.get_evidence(result.get("evidence", ""))
                    except WarrantError as error:
                        problems.append(f"entry {number}: {error}")
        return problems

    def _lines(self) -> list[str]:
        if not self.path.exists():
            return []
        # Split on "\n" only: str.splitlines() also breaks on characters that canonical JSON leaves unescaped.
        return [line for line in self.path.read_text(encoding="utf-8").split("\n") if line]

    def _evidence_path(self, digest: str) -> Path:
        return self.evidence_dir / f"{hex_part(digest)}.json"
