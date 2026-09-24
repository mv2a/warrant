"""The warrant command."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from warrant import __version__, gate, report, scaffold
from warrant.config import load_config, validate_selector
from warrant.errors import WarrantError
from warrant.hashing import short, tree_digest
from warrant.ledger import Ledger
from warrant.project import Project, find_root, load_project
from warrant.verify import run_checks

_INCIDENT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    try:
        code = args.handler(args)
        sys.stdout.flush()
        return code
    except WarrantError as error:
        print(f"warrant: {error}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        # The reader went away (for example `warrant log | head`); that's not an error.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warrant",
        description="Humans state intent. Agents write the code. Evidence decides what ships.",
    )
    parser.add_argument("--version", action="version", version=f"warrant {__version__}")
    parser.add_argument("-C", dest="directory", default=".", metavar="DIR", help="run as if started in DIR")
    commands = parser.add_subparsers(metavar="COMMAND")

    command = commands.add_parser("init", help="create a new project")
    command.add_argument("path", nargs="?", default=".", help="where to create it (default: here)")
    command.add_argument("--name", help="project name (default: the directory's name)")
    command.set_defaults(handler=_init)

    command = commands.add_parser("check", help="validate the intent, checks and policy, and show coverage")
    command.add_argument("--workspace", metavar="DIR", help="check separation against this workspace")
    command.set_defaults(handler=_check)

    command = commands.add_parser("approve", help="approve the current intent, checks and policy (principals only)")
    command.add_argument("--by", required=True, metavar="NAME", help="who is approving")
    command.add_argument("--note", default="", help="why, or what changed")
    command.set_defaults(handler=_approve)

    command = commands.add_parser("brief", help="print the builder's brief, which never includes hidden checks")
    command.add_argument("--out", metavar="FILE", help="write it to FILE")
    command.set_defaults(handler=_brief)

    command = commands.add_parser("verify", help="run checks on a snapshot of the workspace and record evidence")
    command.add_argument("--workspace", metavar="DIR")
    command.add_argument(
        "--audience", choices=("principal", "builder"), default="principal",
        help="builder output reveals hidden checks only as the promises they found broken",
    )
    command.add_argument(
        "--select", action="append", metavar="SELECTOR",
        help="run only matching checks: all, public, holdout, tag:NAME or id:ID (repeatable)",
    )
    command.set_defaults(handler=_verify)

    command = commands.add_parser("gate", help="issue a warrant or a denial for an action such as merge")
    command.add_argument("action", help="a gate defined in warrant.toml")
    command.add_argument("--workspace", metavar="DIR")
    command.set_defaults(handler=_gate)

    command = commands.add_parser("report", help="show which promises are kept and broken")
    command.add_argument("--workspace", metavar="DIR")
    command.add_argument("--audience", choices=("principal", "builder"), default="principal")
    command.add_argument("--out", metavar="FILE", help="write it to FILE")
    command.set_defaults(handler=_report)

    command = commands.add_parser("incident", help="record or list problems found in operation")
    actions = command.add_subparsers(dest="incident_action", metavar="ACTION")
    add = actions.add_parser("add", help="record an incident")
    add.add_argument("id", help="an ID such as INC-1")
    add.add_argument("description", help="what happened, in plain words")
    add.add_argument("--clause", action="append", default=[], metavar="ID", help="a promise involved (repeatable)")
    add.add_argument("--by", required=True, metavar="NAME", help="who is recording it")
    actions.add_parser("list", help="list incidents and their regression checks")
    command.set_defaults(handler=_incident, incident_parser=command)

    command = commands.add_parser("log", help="show the ledger")
    command.add_argument("--verify", action="store_true", help="check that the ledger and evidence are intact")
    command.set_defaults(handler=_log)
    return parser


def _base(args) -> Path:
    base = Path(args.directory).expanduser().resolve()
    if not base.is_dir():
        raise WarrantError(f"-C {args.directory}: not a directory")
    return base


def _project(args) -> Project:
    return load_project(find_root(_base(args)))


def _workspace(args, project: Project) -> tuple[Path, str]:
    if args.workspace:
        path = Path(args.workspace).expanduser()
        path = path if path.is_absolute() else _base(args) / path
    elif project.config.workspace is not None:
        path = project.config.workspace
    else:
        raise WarrantError("no workspace given: pass --workspace DIR or set workspace in warrant.toml")
    if not path.is_dir():
        raise WarrantError(f"workspace {path} is not a directory")
    return path.resolve(), project.config.display(path)


def _emit(text: str, out: str | None, args) -> None:
    if out is None:
        sys.stdout.write(text)
        return
    path = Path(out).expanduser()
    path = path if path.is_absolute() else _base(args) / path
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")


def _init(args) -> int:
    target = Path(args.path).expanduser()
    target = (target if target.is_absolute() else _base(args) / target).resolve()
    name = args.name or target.name
    created = scaffold.create(target, name)
    print(f"Created a Warrant project in {target}:")
    for path in created:
        print(f"  {path.relative_to(target)}")
    print("  workspace/")
    print()
    print("Next:")
    print("  1. Write your promises in intent.md.")
    print("  2. Have an examiner draft checks for them in checks/, or write them yourself.")
    print("  3. Review the checks, then approve:  warrant approve --by YOUR-NAME")
    print("  4. Hand the builder its brief:       warrant brief")
    return 0


def _check(args) -> int:
    project = _project(args)
    config, intent = project.config, project.intent
    ok = True
    print(config.name)
    print(f"  intent      {config.display(intent.path)}: {len(intent.clauses)} promises ({report.section_summary(intent)})")
    visible = sum(check.visibility == "public" for check in project.checks)
    print(f"  checks      {visible} visible, {len(project.checks) - visible} hidden")

    coverage = project.coverage()
    uncovered = [clause for clause, checks in coverage.items() if not checks]
    visible_only = [
        clause for clause, checks in coverage.items()
        if checks and all(check.visibility == "public" for check in checks)
    ]
    if uncovered:
        ok = False
        print(f"  coverage    NOT COVERED: {', '.join(uncovered)}")
    else:
        note = f"; only visible checks cover {', '.join(visible_only)}" if visible_only else ""
        print(f"  coverage    every promise has a check{note}")

    workspace = None
    if args.workspace:
        workspace = Path(args.workspace).expanduser()
        workspace = workspace if workspace.is_absolute() else _base(args) / workspace
    elif config.workspace is not None:
        workspace = config.workspace
    if workspace is None:
        print("  separation  no workspace configured")
    else:
        problems = config.separation_problems(workspace)
        for problem in problems:
            print(f"  separation  PROBLEM: {problem}")
        if problems:
            ok = False
        else:
            print(f"  separation  ok: hidden checks and the ledger are outside {config.display(workspace)}")

    print(f"  approval    {report.approval_line(project)}")
    print(f"  gates       {', '.join(config.gates)}")
    return 0 if ok else 1


def _approve(args) -> int:
    project = _project(args)
    if project.config.workspace is not None:
        problems = project.config.separation_problems(project.config.workspace)
        if problems:
            raise WarrantError("refusing to approve: " + "; ".join(problems))
    state, previous = project.approval_state()
    if state == "current":
        by, at = previous["data"]["by"], report.when(previous["time"])
        print(f"Nothing to approve: {by} approved this exact intent, checks and policy on {at}.")
        return 0
    entry = project.ledger.append("approve", f"principal:{args.by}", {
        "by": args.by,
        "note": args.note,
        "baseline": project.baseline_digest(),
        **project.baseline(),
    })
    print(
        f"Approved {short(entry['data']['baseline'])}: {len(project.intent.clauses)} promises, "
        f"{len(project.checks)} checks and {len(project.config.gates)} gates."
    )
    if state == "stale":
        print("  Changes since the last approval: " + "; ".join(project.changes_since(previous)))
    uncovered = [clause for clause, checks in project.coverage().items() if not checks]
    if uncovered:
        print(f"  Warning: no check covers {', '.join(uncovered)}.")
    print(f"Recorded in ledger entry #{entry['seq']}.")
    return 0


def _brief(args) -> int:
    _emit(report.render_brief(_project(args)), args.out, args)
    return 0


def _verify(args) -> int:
    project = _project(args)
    workspace, label = _workspace(args, project)
    selectors = args.select or ["all"]
    for selector in selectors:
        validate_selector(selector, "--select")
    run = run_checks(project, workspace, label, selectors)
    print(report.render_run(project, run, args.audience))
    if args.audience == "principal" and project.approval_state()[0] != "current":
        print("Note: these checks aren't approved in their current form, so gates won't count this evidence yet.")
    return 0 if all(outcome.result == "pass" for outcome in run.outcomes) else 1


def _gate(args) -> int:
    project = _project(args)
    workspace, label = _workspace(args, project)
    decision = gate.evaluate(project, args.action, tree_digest(workspace))
    entry = gate.record(project, decision, label)
    print(report.render_decision(decision, label, entry))
    return 0 if decision.granted else 1


def _report(args) -> int:
    project = _project(args)
    workspace, label = _workspace(args, project)
    _emit(report.render_report(project, tree_digest(workspace), label, args.audience), args.out, args)
    return 0


def _incident(args) -> int:
    if args.incident_action is None:
        args.incident_parser.print_help()
        return 2
    project = _project(args)
    incidents = project.incidents()
    if args.incident_action == "list":
        if not incidents:
            print("No incidents recorded.")
        for incident in incidents:
            regressions = [check.id for check in project.checks if incident["id"] in check.regression_for]
            print(f"{incident['id']}  {report.when(incident['time'])}  {incident['description']}")
            print(f"    promises: {', '.join(incident['clauses']) or 'none named'}; "
                  f"regression checks: {', '.join(regressions) or 'none yet'}")
        return 0
    if not _INCIDENT_ID.match(args.id):
        raise WarrantError(f"{args.id!r} is not a usable incident ID; try something like INC-1")
    if any(incident["id"] == args.id for incident in incidents):
        raise WarrantError(f"incident {args.id} is already recorded")
    unknown = [clause for clause in args.clause if project.intent.clause(clause) is None]
    if unknown:
        raise WarrantError(f"{project.intent.path.name} does not define {', '.join(unknown)}")
    entry = project.ledger.append("incident", f"principal:{args.by}", {
        "id": args.id,
        "description": args.description,
        "clauses": args.clause,
        "by": args.by,
    })
    print(f"Recorded incident {args.id} in ledger entry #{entry['seq']}.")
    stopped = [name for name, g in project.config.gates.items() if g.require_regressions]
    if stopped:
        print(f"  {', '.join(stopped)} will be denied until an approved check with "
              f'regression_for = ["{args.id}"] passes.')
    if not args.clause:
        print("  It names no promise. If none of the intent covers what went wrong, the intent is missing one.")
    return 0


def _log(args) -> int:
    ledger = Ledger(load_config(find_root(_base(args))).ledger_dir)
    entries = ledger.entries()
    if args.verify:
        problems = ledger.problems()
        if problems:
            print("The ledger has been altered:")
            print("\n".join(f"  - {problem}" for problem in problems))
            return 1
        print(f"Ledger intact: {len(entries)} entries, head {short(ledger.head())}.")
        print("Keep a copy of the head digest where builders can't write, to detect a wholesale rewrite.")
        return 0
    if not entries:
        print("The ledger is empty.")
    for entry in entries:
        print(report.render_entry(entry))
    return 0
