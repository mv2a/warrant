"""H3: members never pay shipping, and everyone else pays exactly $7.50."""

import random

from _quote import call, finish

rng = random.Random(750)
subtotals = [0, 1, 9999, 10000, 10001, 15000, 2500000] + [rng.randint(0, 2500000) for _ in range(23)]
problems = []
for subtotal in subtotals:
    for member, expected in ((True, 0), (False, 750)):
        status, body = call({"subtotal_cents": subtotal, "member": member})
        shipping = body.get("shipping_cents") if isinstance(body, dict) else None
        if status != 0 or shipping != expected:
            problems.append(f"subtotal {subtotal}, member {member}: expected shipping of {expected}, got {shipping!r}")

finish(problems, f"shipping ok: {len(subtotals) * 2} orders")
