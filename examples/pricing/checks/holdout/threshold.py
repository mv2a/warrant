"""H1: the discount applies only above $100.00."""

from _quote import call, finish

# (subtotal, expected discount): amounts whose 10% is a whole number of cents, plus $100.01.
CASES = [(0, 0), (9990, 0), (10000, 0), (10001, 1000), (10010, 1001), (50000, 5000), (1000000, 100000)]
problems = []
for subtotal, expected in CASES:
    for member in (False, True):
        status, body = call({"subtotal_cents": subtotal, "member": member})
        discount = body.get("discount_cents") if isinstance(body, dict) else None
        if status != 0 or discount != expected:
            problems.append(f"subtotal {subtotal}, member {member}: expected a discount of {expected}, got {discount!r}")

finish(problems, f"threshold ok: {len(CASES) * 2} orders")
