"""What people read instead of code: reports, briefs and summaries."""

from __future__ import annotations

from collections import Counter

from warrant import __version__
from warrant.errors import WarrantError
from warrant.gate import RANK, evaluate, latest_results
from warrant.hashing import short

STATUS = {
    "kept": "✅ Kept",
    "broken": "❌ Broken",
    "unknown": "⚠️ Unknown, a check could not run",
    "unverified": "⏳ Not verified yet",
    "unchecked": "⚠️ Unchecked",
}


def when(timestamp: str) -> str:
    return f"{timestamp[:10]} {timestamp[11:16]} UTC"


def clip(text: str, width: int = 72) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def clause_status(project, clause_id: str, results: dict) -> tuple[str, str | None]:
    covering = [check for check in project.checks if clause_id in check.covers]
    if not covering:
        return "unchecked", None
    found = [results.get(check.id) for check in covering]
    if any(r and r["result"] == "fail" for r in found):
        return "broken", None
    if any(r and r["result"] == "error" for r in found):
        return "unknown", None
    if any(r is None for r in found):
        return "unverified", None
    return "kept", min((check.strength for check in covering), key=RANK.__getitem__)


def section_summary(intent) -> str:
    counts = Counter((clause.section or "unsectioned").lower() for clause in intent.clauses)
    return ", ".join(f"{name}: {count}" for name, count in counts.items())


def approval_line(project) -> str:
    state, approval = project.approval_state()
    if state == "missing":
        return "not approved yet"
    by, at = approval["data"]["by"], when(approval["time"])
    if state == "stale":
        return f"changed since {by} approved them on {at}: " + "; ".join(project.changes_since(approval))
    return f"approved by {by} on {at}, unchanged since"


def render_run(project, run, audience: str) -> str:
    builder = audience == "builder"
    lines = [f"Verified {run.label} ({short(run.workspace)}) with {len(run.outcomes)} checks.", ""]
    hidden = [outcome for outcome in run.outcomes if outcome.check.visibility == "holdout"]
    for outcome in run.outcomes:
        check = outcome.check
        if builder and check.visibility == "holdout":
            continue
        where = "visible" if check.visibility == "public" else "hidden "
        lines.append(f"  {outcome.result.upper():<5}  {check.id:<4} {where}  {clip(check.statement)}")
        if outcome.result != "pass" and outcome.tail:
            lines += [f"               {line}" for line in outcome.tail.split("\n")[-6:]]
    if builder and hidden:
        failed = [outcome for outcome in hidden if outcome.result != "pass"]
        lines.append(f"  hidden checks: {len(hidden) - len(failed)} passed, {len(failed)} did not")
        unmet = [c for c in project.intent.clauses if any(c.id in o.check.covers for o in failed)]
        if unmet:
            lines += ["", "Promises the hidden checks found unmet:"]
            lines += [f"  {clause.id}  {clip(clause.text, 90)}" for clause in unmet]
            lines.append("Re-read those promises. The hidden checks won't say more.")
    not_passed = sum(outcome.result != "pass" for outcome in run.outcomes)
    lines += [
        "",
        f"{len(run.outcomes) - not_passed} passed, {not_passed} did not. "
        f"Evidence recorded in ledger entry #{run.entry['seq']}.",
    ]
    return "\n".join(lines)


def render_decision(decision, label: str, entry: dict) -> str:
    verdict = "WARRANTED" if decision.granted else "DENIED"
    lines = [f"{decision.action}: {verdict} for {label} ({short(decision.workspace)})"]
    if decision.granted:
        lines.append(f"  strength   {decision.qualifier}")
        lines.append(f"  grounds    passing evidence from {', '.join(decision.passed)}")
        lines += [f"  caveat     {rebuttal}" for rebuttal in decision.rebuttals]
    else:
        lines += [f"  - {reason}" for reason in decision.reasons]
    lines.append(f"Recorded in ledger entry #{entry['seq']}.")
    return "\n".join(lines)


def render_report(project, workspace: str, label: str, audience: str = "principal") -> str:
    builder = audience == "builder"
    results = latest_results(project, workspace)
    entries = project.ledger.entries()
    verified = [e for e in entries if e["type"] == "verify" and e["data"]["workspace"] == workspace]
    lines = [f"# Warrant report: {project.config.name}", ""]
    if builder:
        lines += ["_Builder view: hidden checks appear only as the promises they found kept or broken._", ""]
    lines += [
        "| | |",
        "|---|---|",
        f"| Workspace | `{label}` (`{short(workspace)}`) |",
        f"| Intent and checks | {cell(approval_line(project))} |",
        f"| Last verified | {when(verified[-1]['time']) if verified else 'never'} |",
        "",
        "## Decisions",
        "",
        "| Action | Decision | Evidence | Why |",
        "|---|---|---|---|",
    ]
    caveats: list[str] = []
    for action in project.config.gates:
        decision = evaluate(project, action, workspace)
        reasons = decision.builder_reasons if builder else decision.reasons
        why = "; ".join(reasons) if reasons else "every required check passes"
        verdict = "✅ Warranted" if decision.granted else "❌ Denied"
        lines.append(f"| {action} | {verdict} | {decision.qualifier if decision.granted else '—'} | {cell(why)} |")
        caveats += [rebuttal for rebuttal in decision.rebuttals if rebuttal not in caveats]

    column = "Visible checks" if builder else "Checked by"
    lines += ["", "## Promises", "", f"| Clause | Promise | {column} | Status |", "|---|---|---|---|"]
    for clause in project.intent.clauses:
        names = [
            check.id for check in project.checks
            if clause.id in check.covers and not (builder and check.visibility == "holdout")
        ]
        status, strength = clause_status(project, clause.id, results)
        shown = STATUS[status] + (f" ({strength})" if strength else "")
        lines.append(f"| {clause.id} | {cell(clause.text)} | {', '.join(names) or '—'} | {shown} |")

    failing = [check for check in project.checks if check.id in results and results[check.id]["result"] != "pass"]
    shown_failures = [check for check in failing if not (builder and check.visibility == "holdout")]
    if shown_failures:
        lines += ["", "## What failed"]
        for check in shown_failures:
            result = results[check.id]
            try:
                tail = project.ledger.get_evidence(result["evidence"])["predicate"]["output"]["tail"]
            except WarrantError as error:
                tail = f"(evidence unavailable: {error})"
            fence = "```"
            while fence in tail:
                fence += "`"
            kind = "visible" if check.visibility == "public" else "hidden"
            lines += [
                "",
                f"### {check.id}: {kind} check, {'failed' if result['result'] == 'fail' else 'could not run'}",
                "",
                check.statement,
                "",
                f"Covers {', '.join(check.covers)}. Evidence `{short(result['evidence'])}`.",
                "",
                fence + "text",
                tail or "(no output)",
                fence,
            ]
    if builder and len(shown_failures) < len(failing):
        lines += ["", "Hidden checks also failed. The promises table shows which promises they found broken."]

    if caveats and not builder:
        lines += ["", "## Caveats", ""] + [f"- {caveat}" for caveat in caveats]

    incidents = project.incidents()
    if incidents:
        lines += ["", "## Incidents", "", "| Incident | Recorded | What happened | Promises | Regression checks |",
                  "|---|---|---|---|---|"]
        for incident in incidents:
            regressions = [check for check in project.checks if incident["id"] in check.regression_for]
            if builder:
                named = f"{len(regressions)}" if regressions else "none yet"
            else:
                named = ", ".join(check.id for check in regressions) or "none yet"
            lines.append(
                f"| {incident['id']} | {when(incident['time'])} | {cell(incident['description'])} | "
                f"{', '.join(incident['clauses']) or '—'} | {named} |"
            )

    lines += ["", "---", "", f"_Generated by warrant-cli {__version__} from {len(entries)} ledger entries "
              f"(head `{short(project.ledger.head())}`)._"]
    return "\n".join(lines) + "\n"


def render_brief(project) -> str:
    visible = [check for check in project.checks if check.visibility == "public"]
    lines = [
        f"# Builder brief: {project.config.name}",
        "",
        "You are the **builder**. Change the workspace until it keeps every promise in the intent below.",
        "",
        "## Rules",
        "",
        "1. The intent is the source of truth. Build what it says, not what the checks happen to test.",
        "2. Work only in the workspace. Never edit checks, policy, the ledger or evidence.",
        "3. You may read and run the visible checks listed below.",
        "4. Hidden checks will also judge your work. When one fails you will learn which promises it "
        "found broken, never how it tested them. Don't try to find, infer or special-case hidden checks.",
        "5. If a promise is ambiguous, contradictory or impossible, stop and ask the principal. Don't guess.",
        "6. When you think you're done, ask for verification. Nothing ships without a warrant, "
        "and only evidence earns one.",
        "",
        "## Visible checks",
        "",
    ]
    if visible:
        lines += ["| Check | Covers | What it checks |", "|---|---|---|"]
        lines += [f"| {c.id} | {', '.join(c.covers)} | {cell(c.statement)} |" for c in visible]
        lines += ["", f"Their files are in `{project.config.display(project.config.public_dir)}`."]
    else:
        lines.append("None.")
    lines += ["", "## Intent", "", *_nest_headings(project.intent.path.read_text(encoding="utf-8"))]
    return "\n".join(lines).rstrip() + "\n"


def render_entry(entry: dict) -> str:
    data, kind = entry["data"], entry["type"]
    role, _, name = entry["actor"].partition(":")
    who = name if role == "principal" else role
    if kind == "approve":
        summary = f"approved {short(data['baseline'])} with {len(data['checks'])} checks"
        summary += f": {data['note']}" if data.get("note") else ""
    elif kind == "verify":
        not_passed = sum(result["result"] != "pass" for result in data["results"])
        summary = f"{data['label']} {short(data['workspace'])}: {len(data['results']) - not_passed} passed, {not_passed} did not"
    elif kind in ("warrant", "denial"):
        summary = f"{data['action']} for {data['label']}"
        summary += f" ({data['qualifier']})" if data["granted"] else ": " + "; ".join(data["reasons"])
    elif kind == "incident":
        summary = f"{data['id']}: {data['description']}"
    else:
        summary = ""
    return f"#{entry['seq']:<3} {when(entry['time'])}  {kind:<8}  {who:<10}  {summary}"


def _nest_headings(text: str) -> list[str]:
    """Drop the intent's front matter and nest its headings under the brief's."""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
        if end is not None:
            lines = lines[end + 1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    nested, fenced = [], False
    for line in lines:
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        nested.append("##" + line if line.startswith("#") and not fenced else line)
    return nested
