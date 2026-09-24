import json
import tempfile
import unittest
from pathlib import Path

from tests.support import ProjectCase, run_cli, write
from warrant.errors import WarrantError
from warrant.hashing import copy_tree, digest_json, tree_digest
from warrant.intent import parse_intent


class IntentTest(unittest.TestCase):
    def parse(self, text):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return parse_intent(write(Path(temp.name) / "intent.md", text))

    def test_clauses_sections_and_continuations(self):
        intent = self.parse("""
            ---
            owner: dana
            ---

            # Shop

            Context that is not a promise.

            ## Goals

            - G1: First goal
              continues here.
            - Not a promise, because it has no ID.

            ## Constraints

            - C12: A constraint.

            ## Out of scope

            - N1: Explicitly not a promise.
        """)
        self.assertEqual(intent.title, "Shop")
        self.assertEqual(intent.meta, {"owner": "dana"})
        self.assertEqual(intent.ids, ["G1", "C12"])
        self.assertEqual(intent.clause("G1").text, "First goal continues here.")
        self.assertEqual(intent.clause("C12").section, "Constraints")

    def test_code_blocks_hold_no_promises(self):
        intent = self.parse("""
            # Shop

            - G1: Real.

            ```
            - G2: Only an example.
            ```
        """)
        self.assertEqual(intent.ids, ["G1"])

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(WarrantError, "G1 is already defined"):
            self.parse("- G1: One.\n- G1: Two.\n")

    def test_an_intent_needs_promises(self):
        with self.assertRaisesRegex(WarrantError, "has no promises"):
            self.parse("# Shop\n\nJust prose.\n")

    def test_any_edit_changes_the_digest(self):
        self.assertNotEqual(self.parse("- G1: One.\n").digest, self.parse("- G1: One. \n").digest)


class HashingTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / "tree"
        write(self.root / "a.txt", "alpha\n")
        write(self.root / "sub" / "b.txt", "beta\n")

    def test_caches_and_version_control_are_ignored(self):
        before = tree_digest(self.root)
        write(self.root / "__pycache__" / "a.pyc", "junk")
        write(self.root / ".git" / "HEAD", "ref: main")
        self.assertEqual(tree_digest(self.root), before)

    def test_content_names_and_executable_bits_all_count(self):
        digests = {tree_digest(self.root)}
        (self.root / "a.txt").write_text("changed\n")
        digests.add(tree_digest(self.root))
        (self.root / "a.txt").rename(self.root / "c.txt")
        digests.add(tree_digest(self.root))
        (self.root / "c.txt").chmod(0o755)
        digests.add(tree_digest(self.root))
        self.assertEqual(len(digests), 4)

    def test_a_copy_has_the_same_digest(self):
        write(self.root / "__pycache__" / "a.pyc", "junk")
        copy_tree(self.root, self.base / "copy")
        self.assertEqual(tree_digest(self.base / "copy"), tree_digest(self.root))
        self.assertFalse((self.base / "copy" / "__pycache__").exists())

    def test_json_digests_ignore_key_order(self):
        self.assertEqual(digest_json({"a": 1, "b": [2, 3]}), digest_json({"b": [2, 3], "a": 1}))


class ValidationTest(ProjectCase):
    def assert_rejected(self, message):
        code, _, err = self.warrant("check")
        self.assertEqual(code, 2, err)
        self.assertIn(message, err)

    def test_unknown_settings_are_rejected(self):
        self.replace("warrant.toml", "cover_all_intent = true", "cover_all_intents = true")
        self.assert_rejected("unknown setting(s) cover_all_intents")

    def test_checks_must_cover_promises_the_intent_defines(self):
        self.add_check("public", "P2", ["G9"], "pass")
        self.assert_rejected("covers G9, which intent.md does not define")

    def test_check_ids_are_unique(self):
        self.add_check("holdout", "P1", ["G1"], "pass")
        self.assert_rejected("check P1 is defined more than once")

    def test_strength_must_be_known(self):
        self.add_check("public", "P2", ["G1"], "pass", strength="vibes")
        self.assert_rejected("strength must be one of judged, tested, proved")

    def test_gates_cannot_depend_on_each_other_in_a_loop(self):
        self.replace("warrant.toml", "[gates.merge]\n", '[gates.merge]\nafter = ["release"]\n')
        self.assert_rejected("in a loop")

    def test_selectors_must_be_known(self):
        self.replace("warrant.toml", 'checks = ["all"]', 'checks = ["everything"]')
        self.assert_rejected("unknown check selector 'everything'")


class LedgerTest(ProjectCase):
    def setUp(self):
        super().setUp()
        self.warrant("approve", "--by", "tester")
        self.warrant("verify")

    def test_an_untouched_ledger_verifies(self):
        code, out, _ = self.warrant("log", "--verify")
        self.assertEqual(code, 0, out)
        self.assertIn("Ledger intact: 2 entries", out)

    def test_editing_an_entry_is_detected(self):
        path = self.root / "ledger" / "ledger.jsonl"
        lines = path.read_text().splitlines()
        lines[0] = lines[0].replace('"by":"tester"', '"by":"mallory"')
        path.write_text("\n".join(lines) + "\n")
        code, out, _ = self.warrant("log", "--verify")
        self.assertEqual(code, 1)
        self.assertIn("entry 2 does not chain to the entry before it", out)

    def test_editing_evidence_is_detected(self):
        evidence = next((self.root / "ledger" / "evidence").glob("*.json"))
        statement = json.loads(evidence.read_text())
        statement["predicate"]["exitCode"] = 99
        evidence.write_text(json.dumps(statement))
        code, out, _ = self.warrant("log", "--verify")
        self.assertEqual(code, 1)
        self.assertIn("no longer matches its digest", out)


class InitTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def test_a_new_project_is_valid_but_earns_nothing_until_real_checks_exist(self):
        self.assertEqual(run_cli("-C", self.base, "init", "shop")[0], 0)
        root = self.base / "shop"
        for name in ("warrant.toml", "intent.md", "checks/public/checks.toml", "checks/holdout/checks.toml"):
            self.assertTrue((root / name).is_file(), name)
        self.assertEqual(run_cli("-C", root, "check")[0], 0)
        self.assertEqual(run_cli("-C", root, "approve", "--by", "me")[0], 0)
        self.assertEqual(run_cli("-C", root, "verify")[0], 1)
        self.assertEqual(run_cli("-C", root, "gate", "merge")[0], 1)

    def test_init_never_overwrites(self):
        run_cli("-C", self.base, "init", "shop")
        code, _, err = run_cli("-C", self.base, "init", "shop")
        self.assertEqual(code, 2)
        self.assertIn("already has", err)
