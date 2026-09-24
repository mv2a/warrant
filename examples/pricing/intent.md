---
owner: dana, head of e-commerce
---

# Checkout pricing

We run a small online shop. At checkout we turn a cart's subtotal into the amount the
customer pays. Bigger orders should feel rewarded, loyal customers should never pay for
shipping, and nobody should ever be charged a wrong or impossible amount.

## Goals

- G1: Orders with a subtotal over $100.00 get 10% off the subtotal.
- G2: Loyalty members never pay for shipping. Everyone else pays a flat $7.50.

## Constraints

- C1: Money is counted in whole cents. A discount that works out to a fraction of a cent
  is rounded down.
- C2: The amount charged is the subtotal, minus the discount, plus shipping. It is never
  negative.
- C3: Invalid requests are refused, never priced. That includes a subtotal that is
  negative, fractional or not a number, a missing field, and a membership flag that
  isn't true or false.
- C4: Pricing runs as a command named `quote` that takes one JSON request and returns one
  JSON response, as described in the published contract.

## Scenarios

- S1: A non-member with a $120.00 cart is charged $115.50: $12.00 off, plus $7.50 shipping.
- S2: A non-member with a cart of exactly $100.00 is charged $107.50, because the discount
  starts above $100.00.
- S3: A loyalty member with a $50.00 cart is charged $50.00.

## Out of scope

- Coupons, taxes, refunds, and currencies other than US dollars.
