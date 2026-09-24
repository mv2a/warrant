"""H4: the charge adds up, and no amount is impossible."""

import random

from _quote import call, finish

rng = random.Random(11550)
subtotals = [0, 1, 10000, 10001] + [rng.randint(0, 5000000) for _ in range(46)]
problems = []
for subtotal in subtotals:
    status, body = call({"subtotal_cents": subtotal, "member": rng.random() < 0.5})
    if status != 0 or not isinstance(body, dict):
        problems.append(f"subtotal {subtotal}: no price (status {status})")
        continue
    discount, shipping, total = body.get("discount_cents"), body.get("shipping_cents"), body.get("total_cents")
    if not all(type(amount) is int for amount in (discount, shipping, total)):
        problems.append(f"subtotal {subtotal}: amounts must be whole cents, got {body!r}")
    elif total != subtotal - discount + shipping:
        problems.append(f"subtotal {subtotal}: charged {total}, but {subtotal} - {discount} + {shipping} is {subtotal - discount + shipping}")
    elif total < 0 or not 0 <= discount <= subtotal or shipping < 0:
        problems.append(f"subtotal {subtotal}: impossible amounts {body!r}")

finish(problems, f"arithmetic ok: {len(subtotals)} orders")
