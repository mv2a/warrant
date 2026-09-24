# Warrant specification

**Version 0.1, draft.** Anything here may change. Feedback is welcome as an [issue](https://github.com/mv2a/warrant/issues).

The key words MUST, MUST NOT, SHOULD and MAY are used as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Purpose

Warrant is a protocol for building software with AI agents, in which humans direct the work without reading the code. Humans state intent. Agents write and maintain the implementation. An action, such as merging or releasing a change, happens only when independent evidence shows that the change keeps the promises the humans made.

A **warrant** is the record that authorizes such an action. The word comes from Stephen Toulmin's model of argument, in which the warrant is the rule that lets evidence support a claim. Here it is also the permission that follows.

## Roles

| Role | Held by | Does | Must not |
|---|---|---|---|
| Principal | A person accountable for the outcome | Writes and amends the intent. Approves checks and policy. Records incidents. Reads reports. | Let an agent approve in their name |
| Builder | A coding agent | Changes the workspace to keep the intent's promises | Read hidden checks, write evidence, or change checks, policy or the ledger |
| Examiner | A tool or agent independent of the builder | Drafts checks for the principal to approve. Runs checks. Records evidence. | Change the workspace it examines |
| Gatekeeper | Deterministic software | Applies the policy to the evidence. Records warrants and denials. | Exercise judgment, including a language model's |

The same agent MUST NOT act as builder and examiner for the same workspace. Several agents MAY share a role.

## Two sides

A project has two sides:

- The **control side** holds the intent, the checks, the policy and the ledger. It belongs to the principal.
- The **workspace** holds the implementation. It belongs to the builder.

Builders receive the workspace, the intent and the visible checks, and nothing else. Hidden checks and the ledger MUST NOT be inside the workspace, and SHOULD be stored where builders cannot read them at all, such as a separate repository.

## Intent

The intent is a Markdown file. Each promise is a **clause**: a top-level bullet (`-` or `*`) that begins with an ID and a colon.

```markdown
## Goals

- G1: Orders with a subtotal over $100.00 get 10% off the subtotal.
- G2: Loyalty members never pay for shipping. Everyone else pays a flat $7.50.
```

- An ID is one to three capital letters followed by one to four digits, such as G1, C12 or SEC3. IDs MUST be unique within the file.
- A clause continues onto the indented lines that follow it.
- The level-two heading above a clause names its section, such as Goals, Constraints or Scenarios. Sections help readers; every clause binds equally.
- List items under a heading that begins with "Out of scope" or "Non-goals" are not clauses.
- Everything else, including prose, other headings, examples and fenced code, is context. It informs builders but makes no promise.
- The file MAY begin with front matter: `key: value` lines between two `---` lines.

Clauses SHOULD be written so that someone could check them. A clause that no check covers is a promise nobody is tracking.

## Checks

A check makes one or more clauses decidable by a machine. Checks live in two directories, each with a `checks.toml` manifest:

- **Visible checks** (`public`) may be read and run by the builder. Use them for contracts and examples the builder needs.
- **Hidden checks** (`holdout`) MUST NOT be seen by the builder. They SHOULD cover every clause that matters.

```toml
[[check]]
id = "H2"
covers = ["C1"]
statement = "Fractional-cent discounts are rounded down, not to the nearest cent."
strength = "tested"
run = ["python3", "rounding.py"]
timeout = 120
tags = ["money"]
regression_for = []
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique across all checks |
| `covers` | yes | The clause IDs this check decides. Each MUST exist in the intent. |
| `statement` | yes | What the check shows, in plain words, for the principal |
| `run` | yes | The command, as a list of strings, or as a string split the way a shell would |
| `strength` | yes | `judged`, `tested` or `proved`; see [evidence strength](#evidence-strength) |
| `timeout` | no | Seconds before the run is stopped. The default is 120. |
| `tags` | no | Labels that policy can select |
| `regression_for` | no | IDs of the incidents this check guards against |

**Running a check.** The examiner copies the workspace snapshot and the check's directory into a fresh temporary directory. It runs `run` with the copied check directory as the working directory and the environment variable `WARRANT_WORKSPACE` set to the copied workspace. Exit status 0 means **pass** and any other status means **fail**. A command that cannot start, or that exceeds its timeout, is an **error**. Output is recorded.

**Check digest.** A check's digest covers its definition and every file in its directory. Changing either makes it a different check, which needs approval.

## Evidence strength

| Strength | Meaning |
|---|---|
| `judged` | A person or a model assessed the result. It may not be reproducible. |
| `tested` | Deterministic checks passed on specific or generated inputs. |
| `proved` | A proof checker verified the property for all inputs, relative to the stated specification and the checker's trusted base. |

Strength is ordered: judged < tested < proved. A check declares its strength, and the principal approves that declaration along with the check. A warrant's strength is the weakest strength among the checks it relies on.

## Policy

Gates are defined in `warrant.toml`, one table per action:

```toml
[gates.merge]
checks = ["all"]
min_strength = "tested"
cover_all_intent = true

[gates.release]
after = ["merge"]
checks = ["tag:payments"]
min_strength = "proved"
require_regressions = true
```

| Setting | Default | Meaning |
|---|---|---|
| `checks` | `["all"]` | Selectors for the checks that must pass: `all`, `public`, `holdout`, `tag:NAME` or `id:ID` |
| `min_strength` | `"tested"` | Every selected check must be at least this strong |
| `after` | `[]` | Gates that must also grant a warrant for the same workspace |
| `cover_all_intent` | `false` | Deny unless a selected check covers every clause |
| `require_regressions` | `false` | Deny unless every recorded incident has a regression check that passes |

Unknown settings are errors, so a typo cannot quietly weaken a gate.

## Baseline and approval

The **baseline** is the digest of the intent's digest, every check's digest, and the policy's digest. A principal approves a baseline by recording an `approve` entry in the ledger.

Only the latest approval counts. If the current baseline differs from it, every gate MUST deny until a principal approves again. This is how principals own the definition of done: agents may draft clauses, checks and policy, but nothing they draft binds until a principal approves it.

## Evidence

Each run of a check produces one evidence statement in the [in-toto](https://github.com/in-toto/attestation) Statement format. Its subject is the exact workspace snapshot that was tested.

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{"name": "workspace", "digest": {"sha256": "fd797c2edfda..."}}],
  "predicateType": "https://github.com/mv2a/warrant/blob/main/SPEC.md#evidence",
  "predicate": {
    "version": "0.1",
    "check": {"id": "H2", "digest": "sha256:...", "visibility": "holdout", "covers": ["C1"], "strength": "tested"},
    "baseline": "sha256:...",
    "result": "pass",
    "exitCode": 0,
    "command": ["python3", "rounding.py"],
    "startedAt": "2026-09-23T14:03:11Z",
    "durationSeconds": 1.84,
    "output": {"digest": "sha256:...", "tail": "rounding ok: 60 orders"},
    "verifier": {"name": "warrant-cli", "version": "0.1.0", "python": "3.13.3"}
  }
}
```

Statements are stored under the digest of their canonical JSON: keys sorted, no insignificant whitespace, UTF-8. The workspace digest covers the path, content and executable bit of every file, ignoring version-control metadata, caches and virtual environments.

Evidence counts toward a gate only when its workspace digest matches the workspace being gated and its check digest matches an approved check. Evidence about anything else is kept but ignored.

## Warrants and denials

The gatekeeper records every decision. A decision is laid out like an argument in Toulmin's model:

| Field | In Toulmin's model | Meaning |
|---|---|---|
| `claim` | claim | What the decision asserts about the workspace |
| `grounds` | grounds | Digests of the passing evidence it relies on |
| `rule` | warrant | The gate policy that was applied |
| `backing` | backing | The approved baseline, who approved it, and the gatekeeper's version |
| `qualifier` | qualifier | The weakest evidence strength relied on |
| `rebuttals` | rebuttal | Known limits, such as clauses that only visible checks cover |
| `reasons` | | For a denial, everything that is missing or failed |

A missing result counts as a failure. The gatekeeper MUST be deterministic: the same ledger and files always produce the same decision.

## Ledger

The ledger is an append-only file of JSON lines, one entry per line, each in canonical form:

```json
{"actor":"gatekeeper:warrant-cli/0.1.0","data":{...},"prev":"sha256:...","seq":5,"time":"2026-09-23T14:03:40Z","type":"warrant"}
```

- `prev` is the digest of the previous line. The first entry uses 64 zeros.
- Entry types are `approve`, `verify`, `warrant`, `denial` and `incident`.
- Evidence is stored beside the ledger and referenced by digest.

Changing, removing or reordering an entry breaks the chain after it. The chain cannot reveal a wholesale rewrite by someone with write access, so principals SHOULD keep a copy of the latest head digest where builders cannot write.

## Incidents

An incident records a problem found in operation. It MAY name the clauses involved. An incident that names none suggests the intent is missing a promise.

A gate with `require_regressions` denies until every incident has at least one approved check whose `regression_for` includes the incident's ID, and that check passes on the workspace. An incident stops the line until it has become a check.

## Feedback to builders

Builders receive full results for visible checks. For hidden checks they learn only whether each passed and, for a failing check, the IDs and text of the clauses it covers. They never see its statement, inputs, output or files.

This keeps hidden checks useful, and pushes builders to satisfy the intent rather than the tests. If the intent doesn't give enough to fix a failure, the intent is ambiguous, and the builder SHOULD ask the principal instead of guessing.

## Lifecycle

1. **Intend.** The principal writes clauses.
2. **Examine.** An examiner drafts visible and hidden checks.
3. **Approve.** The principal reviews the clauses, the check statements and the policy, then approves the baseline.
4. **Build.** The builder changes the workspace, guided by the brief and the visible checks.
5. **Verify.** The examiner runs the checks on a snapshot and records evidence.
6. **Gate.** The gatekeeper issues warrants or denials.
7. **Operate.** Warranted changes ship.
8. **Learn.** Incidents are recorded, turned into regression checks, and approved.

Amending the intent returns to step 1. Nothing is kept on trust: every version of the code earns its own warrant against the current baseline.

## Invariants

A conforming implementation MUST ensure that:

1. Gates deny while the latest approval does not match the current baseline.
2. Evidence counts only for the exact workspace digest and the exact approved check digest it names.
3. A selected check without evidence counts as failed.
4. Hidden checks and the ledger are never inside the builder's workspace, and output meant for builders reveals hidden checks only through the clauses they cover.
5. Gates are deterministic and use no model's judgment.
6. The ledger is only ever appended to.

## Trust model

Version 0.1 is designed to catch builders that overfit to, cut corners on, or game the checks they can see. It does not yet defend against a compromised control side.

- **Code execution.** Verification runs the builder's code with the examiner's permissions, without a sandbox. Untrusted code SHOULD be verified inside a container or virtual machine.
- **Signatures.** Evidence and ledger entries are not signed yet, so their integrity depends on who can write to the control side.
- **Check quality.** Coverage shows that a clause is checked, not that it is checked well. The principal's review of check statements is the root of trust. Hidden checks, mutation testing and independent examiners all strengthen it.
- **Separation.** The reference implementation refuses to run when hidden checks or the ledger are inside the workspace. Beyond that, keeping builders away from the control side is up to the deployment.

## Related work

- Evidence uses the [in-toto Attestation Framework](https://github.com/in-toto/attestation) Statement format, so later versions can sign it with DSSE and Sigstore and work with supply-chain tooling.
- Hidden scenarios kept as a holdout set come from [StrongDM's Software Factory](https://factory.strongdm.ai/).
- The decision record follows Toulmin's model of argument. The approach also echoes [proof-carrying code](https://en.wikipedia.org/wiki/Proof-carrying_code) and [safety cases](https://en.wikipedia.org/wiki/Safety_case).
- [PRIOR-ART.md](PRIOR-ART.md) has the full survey.

## Open questions

- **Validating intent.** How can principals see what their clauses really mean, for example through generated examples, or ambiguity detection like Kiro's requirements analysis?
- **Judged evidence.** When is a scenario evaluated by a language model acceptable, and how should repeated trials be combined?
- **Non-functional promises.** How should latency, cost and security budgets be written as checks?
- **Check quality.** Should mutation scores become evidence about the checks themselves?
- **Independent examiners.** Should high-stakes gates require agreement between examiners built on different models?
- **Identity.** How are principals, examiners and gatekeepers identified, and their records signed?
- **Representations.** Does what builders write in, from mainstream languages to AI-native ones, change how often and how cheaply they earn warrants?
