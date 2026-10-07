# Verification report — `lim-conjugate`

- **Course / topic:** MATH1004 / limits
- **Type:** limit
- **Generated:** 2026-10-07T21:41:35
- **Solution digest:** `5cefe5d518f7f8e0`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 13 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

lim x→0 of (sqrt(x + 4) - 2)/x.

## Steps

**s0 — Set up.** Find the limit as x → 0.

> lim(x→0) (√(x + 4) − 2)/x

**s1 — Multiply by the conjugate.** Multiply top and bottom by the conjugate √(x + 4) + 2 to clear the square root ((A + B)(A − B) = A² − B²).

> lim(x→0) (√(x + 4) − 2)·(√(x + 4) + 2)/(x·(√(x + 4) + 2))

**s2 — Simplify.** Multiply out the product A² − B² and cancel common factors.

> lim(x→0) 1/(√(x + 4) + 2)

**s3 — Direct substitution.** The function is continuous at x = 0, so substitute x = 0.

> 1/(2 + √(4 + 0))

**s4 — Arithmetic.** Simplify.

> 1/4

## Answer: limit

> 1/4


## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 2 | s1 | rewrite keeps the function the same near a | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 3 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 4 | s2 | rewrite keeps the function the same near a | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 1.15e-41) |
| 5 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 6 | s3 | continuous at x = 0 | ✅ PASS | direct substitution is allowed |
| 7 | s3 | substituted value | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 8 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 9 | s4 | arithmetic | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 10 | final | second method: SymPy limit (right) | ✅ PASS | SymPy also gives 1/4 |
| 11 | final | numeric approach from the right | ✅ PASS | f → 0.25, 0.25, 0.25… approaches 1/4 |
| 12 | final | second method: SymPy limit (left) | ✅ PASS | SymPy also gives 1/4 |
| 13 | final | numeric approach from the left | ✅ PASS | f → 0.25, 0.25, 0.25… approaches 1/4 |
