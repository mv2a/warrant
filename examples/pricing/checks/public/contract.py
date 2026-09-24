"""P1: `quote` follows the published contract."""

from _quote import call, finish

FIELDS = {"subtotal_cents", "discount_cents", "shipping_cents", "total_cents"}
problems = []

for request in ({"subtotal_cents": 4200, "member": False}, {"subtotal_cents": 25000, "member": True}):
    status, body = call(request)
    if status != 0:
        problems.append(f"{request}: exited with status {status}, expected 0")
    elif not isinstance(body, dict) or set(body) != FIELDS:
        problems.append(f"{request}: expected an object with exactly {sorted(FIELDS)}, got {body!r}")
    elif not all(type(body[field]) is int for field in FIELDS):
        problems.append(f"{request}: every amount must be a whole number of cents, got {body!r}")
    elif body["subtotal_cents"] != request["subtotal_cents"]:
        problems.append(f"{request}: subtotal_cents must repeat the request, got {body['subtotal_cents']!r}")

status, body = call({"subtotal_cents": -100, "member": False})
if status != 2 or body is not None:
    problems.append(f"a negative subtotal must be refused with status 2 and no output, got status {status} and {body!r}")

finish(problems, "contract ok: 3 requests")
