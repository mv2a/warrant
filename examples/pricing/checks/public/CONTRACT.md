# The `quote` contract

The workspace must contain an executable file named `quote`.

It reads one JSON object from standard input:

    {"subtotal_cents": 12000, "member": false}

- `subtotal_cents` is the cart subtotal in whole US cents, zero or more.
- `member` is `true` for loyalty members and `false` for everyone else.

It writes one JSON object to standard output and exits with status 0:

    {"subtotal_cents": 12000, "discount_cents": 1200, "shipping_cents": 750, "total_cents": 11550}

Every amount is a whole number of cents.

If the request is invalid, `quote` writes nothing to standard output, explains the problem
on standard error, and exits with status 2.
