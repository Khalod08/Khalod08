# Verification report — `def-polynomial`

- **Course / topic:** MATH1004 / integrals
- **Type:** definite_integral
- **Generated:** 2026-10-07T21:44:11
- **Solution digest:** `b89106744c1eedd9`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 26 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Evaluate ∫ from 0 to 2 of 3x^2 + 1 dx.

## Steps

**s0 — Set up.** By the Fundamental Theorem of Calculus, ∫ₐᵇ f = F(b) − F(a) for any antiderivative F. First find F.

> ∫₀² (3x² + 1) dx

**s1 — Sum rule.** Integrate term by term.

> ∫ (3x²) dx + ∫ 1 dx

**s2 — Constant multiple rule.** Pull the constant 3 out of the integral.

> 3·∫ x² dx + ∫ 1 dx

**s3 — Power rule.** ∫ xⁿ dx = xⁿ⁺¹/(n + 1) with n = 2: raise the power by 1 and divide by the new power.

> 3·(x³/3) + ∫ 1 dx

**s4 — Integral of a constant.** ∫ c dx = c·x.

> 3·(x³/3) + 1·x

**s5 — Simplify.** Combine the constants.

> x³ + x

**s6 — Fundamental Theorem: F(b) − F(a).** Evaluate F at the top limit 2 and subtract F at the bottom limit 0.

> (2 + 2³) − (0 + 0³)

**s7 — Arithmetic.** Simplify.

> 10

## Answer: ∫[0→2]

> 10

- Antiderivative used: F(x) = x³ + x. Decimal: ≈ 10.

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s1 | rule applied to an integral in the previous line | ✅ PASS | the rewritten ∫ appears in the previous line |
| 2 | s1 | only this integral changed | ✅ PASS | after = before with just this ∫ replaced |
| 3 | s1 | d/dx of the result = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 4 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 5 | s2 | rule applied to an integral in the previous line | ✅ PASS | the rewritten ∫ appears in the previous line |
| 6 | s2 | only this integral changed | ✅ PASS | after = before with just this ∫ replaced |
| 7 | s2 | d/dx of the result = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 8 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 9 | s3 | rule applied to an integral in the previous line | ✅ PASS | the rewritten ∫ appears in the previous line |
| 10 | s3 | only this integral changed | ✅ PASS | after = before with just this ∫ replaced |
| 11 | s3 | d/dx of the result = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 12 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 13 | s4 | rule applied to an integral in the previous line | ✅ PASS | the rewritten ∫ appears in the previous line |
| 14 | s4 | only this integral changed | ✅ PASS | after = before with just this ∫ replaced |
| 15 | s4 | d/dx of the result = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 16 | s5 | continues from previous step | ✅ PASS | starts from the result of s4 |
| 17 | s5 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 18 | s6 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 19 | s7 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 20 | final | F′(x) = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 21 | final | no ∫ left in the answer | ✅ PASS | fully integrated |
| 22 | final | answer is in terms of x only | ✅ PASS | no substitution variables left |
| 23 | final | second method: SymPy integrate (same up to a constant) | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 24 | final | integrand continuous on [a, b] | ✅ PASS | no discontinuities in the interval (FTC applies) |
| 25 | final | second method: SymPy definite integral | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 26 | final | numerical quadrature | ✅ PASS | mpmath.quad gives 10.0 |
