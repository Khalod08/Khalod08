# Verification report — `derivative-chain-power`

- **Course / topic:** MATH1004 / derivatives
- **Type:** derivative
- **Generated:** 2026-10-07T21:43:38
- **Solution digest:** `b2a55daefbebf1e2`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 37 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Differentiate f(x) = (3x^2 + 1)^5.

f(x) = (3x² + 1)⁵

## Steps

**s0 — Set up.** We want the derivative of f(x) = (3x² + 1)⁵.

> d/dx[(3x² + 1)⁵]

**s1 — Chain rule (power outside).** Chain rule: the outside is (inside)^5, the inside is u = 3x² + 1. Differentiate the outside (power rule), keep the inside, then multiply by du/dx.

> 5(3x² + 1)⁴·d/dx[3x² + 1]

**s2 — Sum/difference rule.** The derivative of a sum is the sum of the derivatives, term by term.

> 5(3x² + 1)⁴·(d/dx[3x²] + d/dx[1])

**s3 — Constant multiple rule.** The constant 3 can be pulled out in front of the derivative.

> 5(3x² + 1)⁴·(3d/dx[x²] + d/dx[1])

**s4 — Power rule.** Power rule: bring down the exponent 2 and lower the power by 1.

> 5(3x² + 1)⁴·(3·2x + d/dx[1])

**s5 — Constant rule.** 1 does not depend on x, so its derivative is 0.

> 5(3x² + 1)⁴·(3·2x + 0)

**s6 — Simplify.** Multiply out the constants and combine like terms.

> 30x·(3x² + 1)⁴

## Answer: f′(x)

> 30x·(3x² + 1)⁴


## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s0 | matches the given function | ✅ PASS | starts from d/dx[(3x² + 1)⁵], the confirmed problem |
| 2 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 3 | s1 | rule matches the expression | ✅ PASS | Chain rule (power outside) applies to (3x² + 1)⁵ |
| 4 | s1 | rule applied to a term in the expression | ✅ PASS | the rewritten d/dx[…] appears in the previous line |
| 5 | s1 | local rewrite vs sympy.diff | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 6 | s1 | only this term changed | ✅ PASS | after = before with just this d/dx[…] replaced |
| 7 | s1 | whole line still equal | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 8 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 9 | s2 | rule matches the expression | ✅ PASS | Sum/difference rule applies to 3x² + 1 |
| 10 | s2 | rule applied to a term in the expression | ✅ PASS | the rewritten d/dx[…] appears in the previous line |
| 11 | s2 | local rewrite vs sympy.diff | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 12 | s2 | only this term changed | ✅ PASS | after = before with just this d/dx[…] replaced |
| 13 | s2 | whole line still equal | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 14 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 15 | s3 | rule matches the expression | ✅ PASS | Constant multiple rule applies to 3x² |
| 16 | s3 | rule applied to a term in the expression | ✅ PASS | the rewritten d/dx[…] appears in the previous line |
| 17 | s3 | local rewrite vs sympy.diff | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 18 | s3 | only this term changed | ✅ PASS | after = before with just this d/dx[…] replaced |
| 19 | s3 | whole line still equal | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 20 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 21 | s4 | rule matches the expression | ✅ PASS | Power rule applies to x² |
| 22 | s4 | rule applied to a term in the expression | ✅ PASS | the rewritten d/dx[…] appears in the previous line |
| 23 | s4 | local rewrite vs sympy.diff | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 24 | s4 | only this term changed | ✅ PASS | after = before with just this d/dx[…] replaced |
| 25 | s4 | whole line still equal | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 26 | s5 | continues from previous step | ✅ PASS | starts from the result of s4 |
| 27 | s5 | rule matches the expression | ✅ PASS | Constant rule applies to 1 |
| 28 | s5 | rule applied to a term in the expression | ✅ PASS | the rewritten d/dx[…] appears in the previous line |
| 29 | s5 | local rewrite vs sympy.diff | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 30 | s5 | only this term changed | ✅ PASS | after = before with just this d/dx[…] replaced |
| 31 | s5 | whole line still equal | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 32 | s6 | continues from previous step | ✅ PASS | starts from the result of s5 |
| 33 | s6 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 34 | final | no d/dx left in the answer | ✅ PASS | answer is fully differentiated |
| 35 | final | last step is the answer | ✅ PASS | the final line is the reported answer |
| 36 | final | second method: sympy.diff | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 37 | final | finite-difference check | ✅ PASS | numerical slope of f matches f′ at 7 random points (max rel. error 1.39e-41) |
