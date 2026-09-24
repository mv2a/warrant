"""P2: the example orders written in the intent."""

from _quote import call, finish

SCENARIOS = [
    ("S1", {"subtotal_cents": 12000, "member": False}, 11550),
    ("S2", {"subtotal_cents": 10000, "member": False}, 10750),
    ("S3", {"subtotal_cents": 5000, "member": True}, 5000),
]
problems = []
for scenario, request, expected in SCENARIOS:
    status, body = call(request)
    charged = body.get("total_cents") if isinstance(body, dict) else None
    if status != 0 or charged != expected:
        problems.append(f"{scenario}: expected a charge of {expected} cents, got {charged!r} (status {status})")

finish(problems, "scenarios ok: S1, S2, S3")
