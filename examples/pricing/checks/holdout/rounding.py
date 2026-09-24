"""H2: fractional-cent discounts are rounded down, never to the nearest cent."""

import random

from _quote import call, finish

rng = random.Random(20260923)
subtotals = [10015, 10019, 12345, 99999, 100005] + [rng.randint(10001, 1000000) for _ in range(55)]
problems = []
for subtotal in subtotals:
    expected = subtotal // 10  # 10%, rounded down to the cent
    status, body = call({"subtotal_cents": subtotal, "member": rng.random() < 0.5})
    discount = body.get("discount_cents") if isinstance(body, dict) else None
    if status != 0 or discount != expected:
        problems.append(f"subtotal {subtotal}: expected a discount of {expected}, got {discount!r}")

finish(problems, f"rounding ok: {len(subtotals)} orders")
