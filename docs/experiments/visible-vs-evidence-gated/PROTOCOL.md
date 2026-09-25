# Pre-registered protocol: visible-test-only agent development versus Warrant's evidence-gated protocol

| | |
|---|---|
| Protocol version | 0.1, draft |
| Written | 25 September 2026 |
| Status | **Not yet registered. No task has been built, no agent has been run and no data exist.** |
| Author | Tiago Miranda de Leão (mv2a). Drafted with AI assistance; see the commit trailers. |

This document fixes the design, the measurements and the analysis before any data are
collected. It becomes a pre-registration when it is frozen: its SHA-256 is recorded, it
is deposited with an external, time-stamping registry, and its registration date is
written into it. It must be frozen before the first builder run. After that, every
change goes in `DEVIATIONS.md` with a date and a reason, and the original text stays
readable.

## 1. Question

When coding agents build software against promises stated in plain language, does
Warrant's protocol ship fewer broken promises than the common practice of accepting
whatever passes the tests the agent can see, and what does it cost in money, time and
delivered work? Under Warrant, hidden checks, promise-level feedback to the builder and a
deterministic gate decide.

## 2. Hypotheses

Primary:

- **H1 (escaped defects).** Runs under Warrant (condition B) ship fewer broken promises
  per run than runs under visible-test-only acceptance (condition A).
- **H2 (false passes).** Condition B accepts a candidate that breaks at least one promise
  less often than condition A.

Guard (so that refusing everything cannot win):

- **G1 (delivery).** The rate at which condition B accepts a candidate that keeps every
  promise is not lower than condition A's by more than 10 percentage points.

Secondary: condition B costs more and takes longer per task than condition A (H3, H4).
Both magnitudes are reported whatever they turn out to be. Warrant's verdicts reproduce
when re-verified on a clean machine (H5).

Exploratory, and labelled as such when reported: the mix of failure modes by condition;
the effect of builder model; and, if condition C is run, how much of any difference comes
from feedback rather than from the gate.

## 3. Design

A paired comparison over a fixed suite of tasks. Each task is run under each condition
by the same builder configuration, with `r = 3` independent replicates per task and
condition. The order of conditions is randomised per task, with the random seed recorded.

| | A: visible-only | B: Warrant | C: gate without feedback (secondary, optional) |
|---|---|---|---|
| Builder sees | intent, visible checks | intent, visible checks | intent, visible checks |
| Feedback between submissions | results of visible checks | results of visible checks, plus the IDs of promises that hidden checks found unmet (`warrant verify --audience builder`), never how | results of visible checks only |
| A candidate is accepted when | every visible check passes | `warrant gate merge` issues a warrant (all approved checks, visible and hidden, pass, and coverage is complete) | as B |
| Submission budget | up to 5 | up to 5 | up to 5 |

Condition C isolates the gate from the feedback. It runs only if the budget allows, and
the decision is recorded before the first run.

## 4. Tasks

**Suite.** A planned 30 tasks, with a minimum of 20. Every task is newly written for this
study, so that no builder can have seen it in training. Each is a small command-line
program, like `examples/pricing`, in one language chosen per task and recorded. Each
task consists of:

- `intent.md`: 5 to 12 numbered promises in plain language;
- **visible checks (V)**: shown to the builder;
- **hidden checks (H)**: approved and used by Warrant's gate in conditions B and C, never
  shown to any builder;
- **audit checks (X)**: a third, independent suite used only to score outcomes, never run
  during development in any condition. It is the ground truth for broken promises;
- a reference implementation.

**Validity gates, applied before any builder run.** The reference implementation must pass
V, H and X. Every promise must be covered by at least one check in X. For each task, a
deliberately broken implementation, one per promise where feasible, must fail X on that
promise. A task that fails a gate is repaired or removed, and the removal is recorded.
After the gates pass, the SHA-256 of every task directory is recorded in
`tasks.lock`, and X stays sealed until all runs are complete.

**Authorship.** The author writes the tasks. At least one person who did not write a
task reviews its intent and its three check suites for ambiguity and gaps before the
suites are sealed. The reviewer is named in the results. If no independent reviewer can
be found, that is reported as a limitation.

## 5. Builders

A builder is a coding agent with a pinned configuration: agent software and version,
model identifier, temperature or equivalent, tool permissions, and system prompt. At least
one builder configuration is run, and a second is run if the budget allows. The
configurations are recorded before the first run. The system prompt is identical across
conditions apart from the condition-specific feedback in §3. Every run starts in a fresh
workspace with no access to V's implementation history, H, X or other runs.
Verification runs in a container, because builder code is untrusted.

Per-run limits: 5 submissions, 45 minutes of wall-clock time and a token cap recorded
with the configuration. A run that hits a limit ends with no accepted candidate.

## 6. Procedure for one run (task, condition, replicate)

1. Create a fresh workspace from the task's starting files. Record its digest.
2. Give the builder the intent and the visible checks.
3. The builder writes code and submits it. Record the workspace digest at submission.
4. Evaluate by condition. A: run V. B and C: run `warrant verify` on the snapshot, then
   `warrant gate merge`.
5. If accepted, stop. If not, and the budget remains, return the condition's feedback and
   go to step 3.
6. At the end, run X against the accepted candidate, or against the last submission if
   none was accepted, and record every promise kept or broken.
7. Record the builder's token usage and the provider's cost, the wall-clock time from
   step 2 to the end, the verification compute time, the number of submissions, the full
   transcript and, in B and C, the ledger.

Infrastructure failures, meaning provider outages or crashes of the harness itself, are
rerun once. A second failure is recorded as a failed run and kept in the data.

## 7. Measurements

| Measure | Definition |
|---|---|
| Escaped defects (per run) | Number of promises X finds broken in the **accepted** candidate. 0 if nothing was accepted. |
| False pass (per run) | 1 if a candidate was accepted and X finds at least one broken promise; otherwise 0. |
| Correct delivery (per run) | 1 if a candidate was accepted and X finds no broken promise; otherwise 0. |
| Acceptance (per run) | 1 if any candidate was accepted. |
| Check coverage (per task) | Share of promises covered by approved checks in V ∪ H, as `warrant check` reports it, plus the share X finds testable. Descriptive. |
| Reproducibility (per accepted B/C run) | Rerun `warrant verify` and `warrant gate` three times on a clean machine against the recorded snapshot: the share of identical verdicts. Also whether `warrant log --verify` passes. |
| Cost (per run) | Builder cost in US dollars at the provider's list prices on the run date, from recorded token counts; verification compute seconds. |
| Latency (per run) | Wall-clock minutes to acceptance, or to the end of the budget. |
| Failure modes | Every broken promise and every denial is coded against a fixed taxonomy: arithmetic or rounding, input validation, boundary, state or ordering, misread intent, visible-test gaming, other. The coder is blind to condition, since runs are labelled with random codes. A second coder codes a random 20% and agreement is reported as Cohen's kappa. |

## 8. Analysis

The unit of analysis is the task. Per-run measures are averaged over the three replicates
within each task and condition.

- **H1.** Wilcoxon signed-rank test on per-task mean escaped defects, B versus A,
  two-sided. The effect is the Hodges–Lehmann estimate of the median paired difference,
  with a 95% bootstrap confidence interval (10,000 resamples over tasks, seed recorded).
- **H2.** Exact McNemar test on paired per-run false-pass outcomes, pairing replicate *i*
  of A with replicate *i* of B within each task. The effect is the difference in
  false-pass rates, with a 95% confidence interval from a cluster bootstrap over tasks.
- **H1 and H2 together.** Holm correction at family-wise α = 0.05.
- **G1.** A one-sided 95% cluster-bootstrap confidence interval for the difference in
  correct-delivery rate, B minus A. G1 holds if its lower bound is above −0.10. If G1
  fails, any H1 or H2 result is reported as coming with lower delivery, not as an
  improvement.
- **H3, H4.** Paired differences in cost and latency, with medians and 95% bootstrap
  confidence intervals. No test.
- **H5.** Share of identical verdicts, with a Wilson confidence interval.
- **Condition C,** if run, is compared with B in the same way and reported as secondary.

**Claims rule.** An effect is claimed only when its confidence interval excludes zero
after correction. Otherwise the result is reported as inconclusive, with the interval.
Results are reported in full whichever direction they go.

**Sample size.** Thirty tasks is a feasibility-scale choice, not the output of a power
analysis. The study can detect only large effects, and it will be described as a pilot.

## 9. Threats to validity

- **One author wrote Warrant, the tasks and this protocol.** Mitigated by the independent
  review in §4, by sealing X, and by publishing every task, check, transcript and ledger.
- **Task realism.** Small command-line tasks are not large systems, and results may not
  transfer. The claim will be limited to tasks of this kind.
- **Leakage through feedback.** In B, promise-level feedback tells the builder where to
  look. That is part of the protocol, not a leak, and condition C measures its
  contribution.
- **Non-determinism and drift.** Agents are stochastic, and models change behind stable
  names. Mitigated by three replicates, pinned configurations and recorded run dates.
- **Audit-suite weakness.** X can miss defects, so escaped defects are a lower bound. The
  broken-implementation gate in §4 is the check on X.

## 10. Materials and data

Published with the results: the tasks (intent, V, H, X, reference implementation,
`tasks.lock`), the builder configurations, the harness, every transcript, every ledger,
the raw per-run table, the analysis scripts and this protocol together with
`DEVIATIONS.md`. X is not published before all runs are complete.

## 11. Conflicts of interest

The author designed and maintains Warrant and has an interest in its looking effective.
That interest is why the design, the metrics, the guard against refusing everything and
the claims rule are fixed here before any data exist.

## 12. Freezing this protocol

1. Finish the open items: builder configurations, token cap, and whether condition C runs.
2. Record the SHA-256 of this file and of `tasks.lock` in `DEVIATIONS.md` under "Frozen".
3. Deposit this file with an external registry that time-stamps it. Record the
   registration identifier and date at the top of this file.
4. Only then start the first builder run.
