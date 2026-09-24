# Working on Warrant

Instructions for coding agents, and people, changing this repository.

- Python 3.11 or newer, standard library only. Don't add dependencies.
- Run the tests before you finish: `python3 -m unittest discover -s tests -t .`
- If you change output or the example, also run `examples/pricing/demo.sh`. It exits non-zero if anything goes differently than expected.
- SPEC.md is normative. A change to a file format, a ledger entry or a gate rule updates SPEC.md in the same commit, and an incompatible change bumps `SPEC_VERSION` in `warrant/verify.py`.
- Keep the example honest. `candidates/overfit` must pass every visible check and fail hidden ones; `candidates/honest` must pass everything. `tests/test_example.py` enforces this.
- The people reading Warrant's output don't read code. Anything printed should use plain words.
