# Verification report — `int-u-sub-cos`

- **Course / topic:** MATH1004 / integrals
- **Type:** indefinite_integral
- **Generated:** 2026-10-07T21:40:34
- **Solution digest:** `65ff60ea0d955423`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 22 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Find ∫ x cos(x^2) dx.

## Steps

**s0 — Set up.** Find all antiderivatives of x·cos(x²).

> ∫ (x·cos(x²)) dx

**s1 — u-substitution.** Let u = x², so du = 2x dx. Rewrite everything in terms of u.

> ∫ (cos(u)/2) du

**s2 — Constant multiple rule.** Pull the constant 1/2 out of the integral.

> ∫ cos(u) du/2

**s3 — Basic antiderivative.** Standard antiderivative: ∫ cos = sin.

> sin(u)/2

**s4 — Substitute back u = x².** Write the answer in terms of the original variable.

> sin(x²)/2

## Answer: ∫ x·cos(x²) dx  (+ C)

> sin(x²)/2

- Every antiderivative is sin(x²)/2 + C.

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s0 | matches the given integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 2 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 3 | s1 | rule applied to an integral in the previous line | ✅ PASS | the rewritten ∫ appears in the previous line |
| 4 | s1 | only this integral changed | ✅ PASS | after = before with just this ∫ replaced |
| 5 | s1 | substitution is valid: g(u(x))·u′(x) = f(x) | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 6 | s1 | new integral is in terms of u only | ✅ PASS | the integrand has no x left |
| 7 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 8 | s2 | rule applied to an integral in the previous line | ✅ PASS | the rewritten ∫ appears in the previous line |
| 9 | s2 | only this integral changed | ✅ PASS | after = before with just this ∫ replaced |
| 10 | s2 | d/dx of the result = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 11 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 12 | s3 | rule applied to an integral in the previous line | ✅ PASS | the rewritten ∫ appears in the previous line |
| 13 | s3 | only this integral changed | ✅ PASS | after = before with just this ∫ replaced |
| 14 | s3 | d/dx of the result = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 15 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 16 | s4 | substituting back u = x² | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 17 | s4 | no u left | ✅ PASS | the answer is in terms of the original variable |
| 18 | final | F′(x) = integrand | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 19 | final | no ∫ left in the answer | ✅ PASS | fully integrated |
| 20 | final | answer is in terms of x only | ✅ PASS | no substitution variables left |
| 21 | final | second method: SymPy integrate (same up to a constant) | ✅ PASS | simplify(before − after) = 0; 7 random points agree (max rel. error 0.0) |
| 22 | final | numerical integration check | ✅ PASS | F(b) − F(a) = numerical ∫ on 6 random intervals (max rel. error 5.74e-42) |
