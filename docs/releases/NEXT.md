<!-- DRAFT release notes for the next release. Not tagged, not released. The version
number is a proposal. Publishing a GitHub release runs .github/workflows/publish.yml,
which uploads warrant-cli to PyPI; see AGENTS.md before releasing. -->

# Warrant v0.1.1 (proposed)

This release adds documentation and metadata only. The command-line tool, the
specification and `SPEC_VERSION` are unchanged from v0.1.0.

**Added**

- `CITATION.cff`, so that GitHub offers "Cite this repository", and `.zenodo.json`, so
  that a release can be archived with a DOI.
- [A draft pre-registered protocol](../experiments/visible-vs-evidence-gated/PROTOCOL.md)
  for a controlled comparison of coding agents under two regimes. In the first, work is
  accepted when the tests the agent can see pass. In the second, Warrant's hidden checks,
  promise-level feedback and deterministic gate decide. The protocol fixes the task suite
  rules, the conditions, the measures (escaped defects, false passes, check coverage,
  reproducibility, cost, latency and failure modes) and the analysis before any data
  exist. **No experiment has been run, and the protocol reports no results.**

**Unchanged limitations.** Checks run without a sandbox, and evidence is not signed yet.
