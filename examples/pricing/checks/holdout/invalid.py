"""H5: invalid requests are refused, never priced."""

from _quote import call, finish

INVALID = [
    ("a negative subtotal", '{"subtotal_cents": -1, "member": false}'),
    ("a fractional subtotal", '{"subtotal_cents": 120.5, "member": false}'),
    ("a subtotal written as text", '{"subtotal_cents": "12000", "member": false}'),
    ("a subtotal of true", '{"subtotal_cents": true, "member": false}'),
    ("a missing subtotal", '{"member": false}'),
    ("a missing membership flag", '{"subtotal_cents": 12000}'),
    ('a membership flag of "yes"', '{"subtotal_cents": 12000, "member": "yes"}'),
    ("a membership flag of 1", '{"subtotal_cents": 12000, "member": 1}'),
    ("text that isn't JSON", "twelve thousand dollars"),
    ("a list instead of an object", "[12000, false]"),
]
problems = []
for name, raw in INVALID:
    status, body = call(raw=raw)
    if status != 2 or body is not None:
        problems.append(f"{name}: expected a refusal (status 2, no output), got status {status} and {body!r}")

finish(problems, f"refusals ok: {len(INVALID)} invalid requests")
