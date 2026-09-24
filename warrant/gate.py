"""The gatekeeper: deterministic rules that turn evidence into warrants or denials."""

from __future__ import annotations

from dataclasses import dataclass, field

from warrant import __version__
from warrant.config import STRENGTHS
from warrant.errors import WarrantError
from warrant.hashing import short

RANK = {strength: rank for rank, strength in enumerate(STRENGTHS)}
GATEKEEPER = f"gatekeeper:warrant-cli/{__version__}"


@dataclass
class Decision:
    action: str
    workspace: str
    baseline: str
    approval: dict | None
    granted: bool = False
    qualifier: str | None = None
    reasons: list[str] = field(default_factory=list)
    builder_reasons: list[str] = field(default_factory=list)  # the same, naming hidden checks only by promise
    rebuttals: list[str] = field(default_factory=list)
    grounds: list[str] = field(default_factory=list)  # evidence digests
    passed: list[str] = field(default_factory=list)  # the checks that evidence came from
    checks: list[str] = field(default_factory=list)

    def deny(self, reason: str, builder_reason: str | None = None) -> None:
        if reason not in self.reasons:
            self.reasons.append(reason)
        builder_reason = builder_reason or reason
        if builder_reason not in self.builder_reasons:
            self.builder_reasons.append(builder_reason)


def latest_results(project, workspace: str) -> dict[str, dict]:
    """The most recent result for each current check on exactly this workspace."""
    current = {check.id: check.digest for check in project.checks}
    results = {}
    for entry in project.ledger.entries():
        if entry["type"] != "verify" or entry["data"]["workspace"] != workspace:
            continue
        for result in entry["data"]["results"]:
            if current.get(result["check"]) == result["digest"]:
                results[result["check"]] = result
    return results


def evaluate(project, action: str, workspace: str) -> Decision:
    gate = project.config.gates.get(action)
    if gate is None:
        raise WarrantError(f"no gate named {action!r}; warrant.toml defines {', '.join(project.config.gates)}")
    state, approval = project.approval_state()
    decision = Decision(action, workspace, project.baseline_digest(), approval)

    if state == "missing":
        decision.deny("nobody has approved the intent and checks yet")
    elif state == "stale":
        decision.deny("changed since approval: " + "; ".join(project.changes_since(approval)))

    for prerequisite in gate.after:
        if not evaluate(project, prerequisite, workspace).granted:
            decision.deny(f"needs a {prerequisite} warrant first")

    results = latest_results(project, workspace)
    selected = [check for check in project.checks if any(check.matches(s) for s in gate.checks)]
    decision.checks = [check.id for check in selected]
    if not selected:
        decision.deny("this gate selects no checks")
    for check in selected:
        _require_pass(decision, check, results.get(check.id))
        if RANK[check.strength] < RANK[gate.min_strength]:
            needs = f"is only {check.strength}; {action} needs {gate.min_strength} evidence"
            decision.deny(f"{check.id} {needs}", f"{_named(check)} {needs}")

    covered = {clause for check in selected for clause in check.covers}
    uncovered = [clause for clause in project.intent.ids if clause not in covered]
    if uncovered and gate.cover_all_intent:
        decision.deny("no check covers " + ", ".join(uncovered))
    elif uncovered:
        decision.rebuttals.append(f"the {action} gate does not check " + ", ".join(uncovered))

    if gate.require_regressions:
        for incident in project.incidents():
            regressions = [check for check in project.checks if incident["id"] in check.regression_for]
            if not regressions:
                decision.deny(f"incident {incident['id']} has no regression check")
            for check in regressions:
                _require_pass(decision, check, results.get(check.id))

    def only(predicate) -> list[str]:
        return [
            clause for clause in project.intent.ids
            if clause in covered and all(predicate(check) for check in selected if clause in check.covers)
        ]

    visible_only = only(lambda check: check.visibility == "public")
    if visible_only:
        decision.rebuttals.append("only checks the builder could see cover " + ", ".join(visible_only))
    judged_only = only(lambda check: check.strength == "judged")
    if judged_only:
        decision.rebuttals.append("only judged, non-reproducible evidence covers " + ", ".join(judged_only))

    if selected:
        decision.qualifier = min((check.strength for check in selected), key=RANK.__getitem__)
    decision.granted = not decision.reasons
    return decision


def record(project, decision: Decision, label: str) -> dict:
    """Write the decision to the ledger, structured the way Toulmin structures an argument."""
    approval = decision.approval
    verb = "keeps" if decision.granted else "has not shown that it keeps"
    data = {
        "action": decision.action,
        "granted": decision.granted,
        "claim": f"Workspace {short(decision.workspace)} ({label}) {verb} every promise the {decision.action} gate requires.",
        "workspace": decision.workspace,
        "label": label,
        "grounds": decision.grounds,
        "rule": {"gate": decision.action, **project.config.gates[decision.action].policy()},
        "backing": {
            "baseline": decision.baseline,
            "approvedBy": approval["data"]["by"] if approval else None,
            "approvalEntry": approval["seq"] if approval else None,
            "gatekeeper": f"warrant-cli/{__version__}",
        },
        "qualifier": decision.qualifier if decision.granted else None,
        "rebuttals": decision.rebuttals,
        "reasons": decision.reasons,
    }
    return project.ledger.append("warrant" if decision.granted else "denial", GATEKEEPER, data)


def _require_pass(decision: Decision, check, result: dict | None) -> None:
    if result is None:
        decision.deny(f"{check.id} has not been run on this workspace", f"{_named(check)} has not been run on this workspace")
    elif result["result"] != "pass":
        verb = "failed" if result["result"] == "fail" else "could not run"
        decision.deny(f"{check.id} {verb}", f"{_named(check)} {verb}")
    elif result["evidence"] not in decision.grounds:
        decision.grounds.append(result["evidence"])
        decision.passed.append(check.id)


def _named(check) -> str:
    """How a builder hears about a check: hidden ones only by the promises they cover."""
    return check.id if check.visibility == "public" else "a hidden check on " + ", ".join(check.covers)
