"""The examiner: run checks against an exact snapshot of a workspace and record the evidence."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from warrant import __version__
from warrant.checks import Check
from warrant.errors import WarrantError
from warrant.hashing import copy_tree, digest_bytes, hex_part, tree_digest
from warrant.ledger import utc_now

STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
EVIDENCE_TYPE = "https://github.com/mv2a/warrant/blob/main/SPEC.md#evidence"
SPEC_VERSION = "0.1"
TAIL_LINES = 40


@dataclass
class Outcome:
    check: Check
    result: str  # "pass", "fail" or "error"
    evidence: str
    tail: str


@dataclass
class Run:
    workspace: str
    label: str
    outcomes: list[Outcome]
    entry: dict


def run_checks(project, workspace: Path, label: str, selectors: list[str]) -> Run:
    problems = project.config.separation_problems(workspace)
    if problems:
        raise WarrantError("refusing to verify: " + "; ".join(problems))
    checks = [check for check in project.checks if any(check.matches(s) for s in selectors)]
    if not checks:
        raise WarrantError("no checks match " + ", ".join(selectors))
    baseline = project.baseline_digest()
    with tempfile.TemporaryDirectory(prefix="warrant-") as temp:
        snapshot = Path(temp) / "snapshot"
        copy_tree(workspace, snapshot)
        digest = tree_digest(snapshot)
        outcomes = [
            _run(project, check, snapshot, digest, baseline, Path(temp) / f"run-{number}")
            for number, check in enumerate(checks, start=1)
        ]
    entry = project.ledger.append("verify", f"examiner:warrant-cli/{__version__}", {
        "workspace": digest,
        "label": label,
        "baseline": baseline,
        "results": [
            {
                "check": outcome.check.id,
                "digest": outcome.check.digest,
                "visibility": outcome.check.visibility,
                "result": outcome.result,
                "evidence": outcome.evidence,
            }
            for outcome in outcomes
        ],
    })
    return Run(digest, label, outcomes, entry)


def _run(project, check: Check, snapshot: Path, workspace_digest: str, baseline: str, directory: Path) -> Outcome:
    # Every check gets fresh copies, so no check can affect another or the snapshot.
    workspace, check_dir = directory / "workspace", directory / "check"
    copy_tree(snapshot, workspace)
    copy_tree(check.directory, check_dir)
    env = dict(os.environ, WARRANT_WORKSPACE=str(workspace), WARRANT_CHECK_ID=check.id, PYTHONDONTWRITEBYTECODE="1")
    started, clock, exit_code = utc_now(), time.monotonic(), None
    try:
        completed = subprocess.run(
            check.run, cwd=check_dir, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=check.timeout,
        )
        output, exit_code = completed.stdout, completed.returncode
        result = "pass" if exit_code == 0 else "fail"
    except subprocess.TimeoutExpired as expired:
        output = (expired.stdout or b"") + f"\n[warrant] stopped after the {check.timeout}s timeout\n".encode()
        result = "error"
    except OSError as error:
        output = f"[warrant] could not start {check.run[0]!r}: {error.strerror or error}\n".encode()
        result = "error"
    text = output.decode("utf-8", errors="replace").rstrip()
    tail = "\n".join(text.split("\n")[-TAIL_LINES:]) if text else ""
    statement = {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": "workspace", "digest": {"sha256": hex_part(workspace_digest)}}],
        "predicateType": EVIDENCE_TYPE,
        "predicate": {
            "version": SPEC_VERSION,
            "check": {
                "id": check.id,
                "digest": check.digest,
                "visibility": check.visibility,
                "covers": check.covers,
                "strength": check.strength,
            },
            "baseline": baseline,
            "result": result,
            "exitCode": exit_code,
            "command": check.run,
            "startedAt": started,
            "durationSeconds": round(time.monotonic() - clock, 3),
            "output": {"digest": digest_bytes(output), "tail": tail},
            "verifier": {"name": "warrant-cli", "version": __version__, "python": platform.python_version()},
        },
    }
    return Outcome(check, result, project.ledger.put_evidence(statement), tail)
