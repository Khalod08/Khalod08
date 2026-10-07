# Verification report — `riemann-right`

- **Course / topic:** MATH1004 / integrals
- **Type:** riemann_sum
- **Generated:** 2026-10-07T21:42:06
- **Solution digest:** `80926e948c0eb5c9`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 8 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

right sum for x^2 on [0,2], n = 4.

## Steps

**s1 — Δx = (b − a)/n.** Width of each of the 4 rectangles.

> 1/2

**s2 — Sample points.** Right endpoints: 1/2, 1, 3/2, 2.

> 1/2, 1, 3/2, 2

**s3 — f(x₀).** f at x = 1/2.

> 1/4

**s4 — f(x₁).** f at x = 1.

> 1

**s5 — f(x₂).** f at x = 3/2.

> 9/4

**s6 — f(x₃).** f at x = 2.

> 4

**s7 — Sum = Δx·(f(x₁) + … ).** Add the heights and multiply by the width.

> 15/4

## Answer: right sum

> 15/4

- ≈ 3.75. For comparison, the exact area ∫ = 8/3 ≈ 2.66667.

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s1 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 2 | s3 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 3 | s4 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 4 | s5 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 5 | s6 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 6 | s7 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 7 | final | second method: recompute the sum | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 8 | final | floating-point cross-check | ✅ PASS | ≈ 3.75 |
