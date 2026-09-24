# Example: checkout pricing

A small shop's pricing rules, built the Warrant way.

- [`intent.md`](intent.md) has nine promises, written by the principal.
- [`checks/public`](checks/public) holds two visible checks and the published [contract](checks/public/CONTRACT.md).
- [`checks/holdout`](checks/holdout) holds five hidden checks. In a real project they would live where builders can't read them.
- [`candidates`](candidates) holds two implementations written by coding agents. You don't need to read them. That's the point.
- [`warrant.toml`](warrant.toml) is the policy. Merging needs every check to pass and every promise to have a check. Releasing also needs a passing regression check for every recorded incident.

Run the walkthrough from the repository root:

```bash
examples/pricing/demo.sh
```

Candidate `overfit` passes every check it can see, and is still refused: hidden checks find that it breaks C1 (rounding) and C3 (refusing invalid requests). Candidate `honest` earns warrants for merge and release, until a production incident stops releases.
