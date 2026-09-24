import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.support import REPO, run_cli


class PricingExampleTest(unittest.TestCase):
    """Keeps the example honest: `overfit` passes every visible check and still breaks promises."""

    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._temp.name) / "pricing"
        shutil.copytree(REPO / "examples" / "pricing", cls.root, ignore=shutil.ignore_patterns("ledger"))
        assert run_cli("-C", cls.root, "approve", "--by", "dana")[0] == 0
        cls.overfit = run_cli("-C", cls.root, "verify", "--workspace", "candidates/overfit")
        cls.honest = run_cli("-C", cls.root, "verify", "--workspace", "candidates/honest")

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    def warrant(self, *args):
        return run_cli("-C", self.root, *args)

    def results(self, label):
        lines = (self.root / "ledger" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        entries = [json.loads(line) for line in lines]
        verify = next(e for e in reversed(entries) if e["type"] == "verify" and e["data"]["label"] == label)
        return {result["check"]: result["result"] for result in verify["data"]["results"]}

    def test_overfit_passes_every_visible_check_and_breaks_two_promises(self):
        self.assertEqual(self.overfit[0], 1)
        results = self.results("candidates/overfit")
        self.assertEqual(results["P1"], "pass")
        self.assertEqual(results["P2"], "pass")
        self.assertEqual({check for check, result in results.items() if result != "pass"}, {"H2", "H5"})

        code, out, _ = self.warrant("gate", "merge", "--workspace", "candidates/overfit")
        self.assertEqual(code, 1)
        self.assertIn("H2 failed", out)
        self.assertIn("H5 failed", out)

        code, report, _ = self.warrant("report", "--workspace", "candidates/overfit")
        self.assertEqual(code, 0)
        for clause in ("C1", "C3"):
            self.assertRegex(report, rf"\| {clause} \|.*❌ Broken")
        for clause in ("G1", "G2", "C2", "C4", "S1", "S2", "S3"):
            self.assertRegex(report, rf"\| {clause} \|.*✅ Kept")

    def test_honest_earns_merge_and_release(self):
        self.assertEqual(self.honest[0], 0)
        self.assertEqual(set(self.results("candidates/honest").values()), {"pass"})
        self.assertEqual(self.warrant("gate", "merge", "--workspace", "candidates/honest")[0], 0)
        self.assertEqual(self.warrant("gate", "release", "--workspace", "candidates/honest")[0], 0)
