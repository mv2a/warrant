"""Shared helpers, including a tiny project whose builder must put 42 in answer.txt."""

import contextlib
import io
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from warrant.cli import main

REPO = Path(__file__).resolve().parent.parent

CONFIG = """
    [project]
    name = "Answer"
    workspace = "good"

    [checks]
    public = "checks/public"
    holdout = "checks/holdout"

    [gates.merge]
    checks = ["all"]
    cover_all_intent = true

    [gates.release]
    after = ["merge"]
    require_regressions = true
"""

INTENT = """
    # Answer

    ## Goals

    - G1: The workspace has a file named answer.txt.
    - G2: answer.txt contains the number 42.
"""

HAS_FILE = """
    import os, sys
    path = os.path.join(os.environ["WARRANT_WORKSPACE"], "answer.txt")
    sys.exit(0 if os.path.exists(path) else "answer.txt is missing")
"""

IS_42 = """
    import os, sys
    path = os.path.join(os.environ["WARRANT_WORKSPACE"], "answer.txt")
    found = open(path).read().strip() if os.path.exists(path) else ""
    if found != "42":
        print(f"secret detail: expected 42, found {found!r}")
        sys.exit(1)
"""


def write(path: Path, text: str, executable: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
    if executable:
        path.chmod(0o755)
    return path


def run_cli(*args) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([str(arg) for arg in args])
    return code, out.getvalue(), err.getvalue()


class ProjectCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        write(self.root / "warrant.toml", CONFIG)
        write(self.root / "intent.md", INTENT)
        self.add_check("public", "P1", ["G1"], HAS_FILE)
        self.add_check("holdout", "H1", ["G2"], IS_42)
        write(self.root / "good" / "answer.txt", "42\n")
        write(self.root / "bad" / "answer.txt", "41\n")

    def add_check(self, visibility, check_id, covers, code, strength="tested", extra=""):
        directory = self.root / "checks" / visibility
        script = f"{check_id.lower()}.py"
        write(directory / script, code)
        entry = (
            f'[[check]]\nid = "{check_id}"\ncovers = {json.dumps(covers)}\n'
            f'statement = "Statement for {check_id}."\nstrength = "{strength}"\n'
            f"run = {json.dumps([sys.executable, script])}\n{extra}\n"
        )
        with (directory / "checks.toml").open("a", encoding="utf-8") as handle:
            handle.write(entry)

    def replace(self, relative, old, new):
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def warrant(self, *args):
        return run_cli("-C", self.root, *args)

    def ledger(self):
        text = (self.root / "ledger" / "ledger.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines()]
