from tests.support import IS_42, ProjectCase, run_cli, write


class GateTest(ProjectCase):
    def test_evidence_does_not_count_until_a_principal_approves(self):
        self.assertEqual(self.warrant("verify")[0], 0)
        code, out, _ = self.warrant("gate", "merge")
        self.assertEqual(code, 1)
        self.assertIn("nobody has approved", out)

    def test_a_failing_hidden_check_denies_and_passing_everything_warrants(self):
        self.warrant("approve", "--by", "tester")
        self.assertEqual(self.warrant("verify", "--workspace", "bad")[0], 1)
        code, out, _ = self.warrant("gate", "merge", "--workspace", "bad")
        self.assertEqual(code, 1)
        self.assertIn("H1 failed", out)

        self.assertEqual(self.warrant("verify")[0], 0)
        code, out, _ = self.warrant("gate", "merge")
        self.assertEqual(code, 0, out)
        self.assertIn("WARRANTED", out)
        self.assertEqual(self.warrant("gate", "release")[0], 0)

        warrant = self.ledger()[-1]
        self.assertEqual(warrant["type"], "warrant")
        self.assertEqual(warrant["data"]["qualifier"], "tested")
        self.assertEqual(len(warrant["data"]["grounds"]), 2)
        self.assertEqual(warrant["data"]["backing"]["approvedBy"], "tester")

    def test_evidence_is_bound_to_the_exact_workspace(self):
        self.warrant("approve", "--by", "tester")
        self.warrant("verify")
        write(self.root / "good" / "notes.txt", "a change nobody verified\n")
        code, out, _ = self.warrant("gate", "merge")
        self.assertEqual(code, 1)
        self.assertIn("has not been run on this workspace", out)

    def test_changing_a_check_voids_the_approval_and_the_old_evidence(self):
        self.warrant("approve", "--by", "tester")
        self.warrant("verify")
        self.assertEqual(self.warrant("gate", "merge")[0], 0)

        script = self.root / "checks" / "holdout" / "h1.py"
        script.write_text(script.read_text() + "# tightened\n")
        code, out, _ = self.warrant("gate", "merge")
        self.assertEqual(code, 1)
        self.assertIn("changed since approval: check H1 changed", out)

        self.warrant("approve", "--by", "tester")
        code, out, _ = self.warrant("gate", "merge")
        self.assertEqual(code, 1)
        self.assertIn("H1 has not been run on this workspace", out)

        self.warrant("verify")
        self.assertEqual(self.warrant("gate", "merge")[0], 0)

    def test_approving_twice_without_changes_records_nothing(self):
        self.warrant("approve", "--by", "tester")
        code, out, _ = self.warrant("approve", "--by", "tester")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to approve", out)
        self.assertEqual(len(self.ledger()), 1)

    def test_a_promise_without_a_check_blocks_merge(self):
        intent = self.root / "intent.md"
        intent.write_text(intent.read_text() + "- G3: answer.txt ends with a newline.\n")
        self.warrant("approve", "--by", "tester")
        self.warrant("verify")
        code, out, _ = self.warrant("gate", "merge")
        self.assertEqual(code, 1)
        self.assertIn("no check covers G3", out)

    def test_an_incident_stops_release_until_its_regression_check_passes(self):
        self.warrant("approve", "--by", "tester")
        self.warrant("verify")
        self.assertEqual(self.warrant("gate", "release")[0], 0)

        code, _, _ = self.warrant("incident", "add", "INC-1", "Customers saw 41", "--clause", "G2", "--by", "tester")
        self.assertEqual(code, 0)
        code, out, _ = self.warrant("gate", "release")
        self.assertEqual(code, 1)
        self.assertIn("incident INC-1 has no regression check", out)
        self.assertEqual(self.warrant("gate", "merge")[0], 0)

        self.add_check("holdout", "H2", ["G2"], IS_42, extra='regression_for = ["INC-1"]')
        self.warrant("approve", "--by", "tester", "--note", "regression check for INC-1")
        self.warrant("verify")
        self.assertEqual(self.warrant("gate", "release")[0], 0)

    def test_incidents_must_name_real_promises_and_be_unique(self):
        code, _, err = self.warrant("incident", "add", "INC-1", "x", "--clause", "G9", "--by", "tester")
        self.assertEqual(code, 2)
        self.assertIn("does not define G9", err)
        self.assertEqual(self.warrant("incident", "add", "INC-1", "x", "--by", "tester")[0], 0)
        code, _, err = self.warrant("incident", "add", "INC-1", "again", "--by", "tester")
        self.assertEqual(code, 2)
        self.assertIn("already recorded", err)

    def test_a_gate_can_demand_stronger_evidence(self):
        self.replace("warrant.toml", "require_regressions = true", 'require_regressions = true\nmin_strength = "proved"')
        self.warrant("approve", "--by", "tester")
        self.warrant("verify")
        self.assertEqual(self.warrant("gate", "merge")[0], 0)
        code, out, _ = self.warrant("gate", "release")
        self.assertEqual(code, 1)
        self.assertIn("P1 is only tested; release needs proved evidence", out)

    def test_hidden_checks_must_live_outside_the_workspace(self):
        code, _, err = self.warrant("verify", "--workspace", ".")
        self.assertEqual(code, 2)
        self.assertIn("inside the builder's workspace", err)
        self.assertEqual(self.warrant("check", "--workspace", ".")[0], 1)

    def test_commands_find_the_project_from_a_subdirectory(self):
        code, out, _ = run_cli("-C", self.root / "good", "check")
        self.assertEqual(code, 0, out)
        self.assertIn("every promise has a check", out)

    def test_unknown_gate(self):
        code, _, err = self.warrant("gate", "deploy")
        self.assertEqual(code, 2)
        self.assertIn("no gate named 'deploy'", err)


class BuilderViewTest(ProjectCase):
    LEAKS = ("secret detail", "H1", "Statement for H1")

    def test_builder_output_names_promises_never_hidden_checks(self):
        self.warrant("approve", "--by", "tester")
        code, out, _ = self.warrant("verify", "--workspace", "bad", "--audience", "builder")
        self.assertEqual(code, 1)
        self.assertIn("G2", out)
        for leak in self.LEAKS:
            self.assertNotIn(leak, out)

        code, report, _ = self.warrant("report", "--workspace", "bad", "--audience", "builder")
        self.assertEqual(code, 0)
        self.assertIn("❌ Broken", report)
        self.assertIn("a hidden check on G2 failed", report)
        for leak in self.LEAKS:
            self.assertNotIn(leak, report)

        code, report, _ = self.warrant("report", "--workspace", "bad")
        self.assertIn("secret detail", report)
        self.assertIn("H1 failed", report)

    def test_the_brief_never_mentions_hidden_checks(self):
        code, brief, _ = self.warrant("brief")
        self.assertEqual(code, 0)
        self.assertIn("P1", brief)
        self.assertIn("- G2: answer.txt contains the number 42.", brief)
        for leak in self.LEAKS:
            self.assertNotIn(leak, brief)
