# Verification report — `complex-cube-roots-of-minus-8`

- **Course / topic:** MATH1104 / complex-numbers
- **Type:** complex
- **Generated:** 2026-10-07T21:38:18
- **Solution digest:** `1c519df85b2ac6d0`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 16 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Find the cube roots of −8.

## Steps

**s1 — Modulus r = √(a² + b²).** Here a = −8 and b = 0.

> 8

**s2 — Argument θ.** The point (−8, 0) lies on an axis, so θ = π.

> π

**s3 — Root k = 0.** z_k = r^(1/3)·(cos((θ + 2πk)/3) + i sin((θ + 2πk)/3)) with k = 0: angle π/3.

> 8^(1/3)·(cos(π/3) + i·sin(π/3))

**s4 — z₀ in a + bi form.** Evaluate cos and sin exactly.

> 1 + √3i

**s5 — Root k = 1.** z_k = r^(1/3)·(cos((θ + 2πk)/3) + i sin((θ + 2πk)/3)) with k = 1: angle π.

> 8^(1/3)·(cos(π) + i·sin(π))

**s6 — z₁ in a + bi form.** Evaluate cos and sin exactly.

> −2

**s7 — Root k = 2.** z_k = r^(1/3)·(cos((θ + 2πk)/3) + i sin((θ + 2πk)/3)) with k = 2: angle 5π/3.

> 8^(1/3)·(cos(5π/3) + i·sin(5π/3))

**s8 — z₂ in a + bi form.** Evaluate cos and sin exactly.

> 1 − √3i

## Answer: the 3 roots

> 1 + √3i, −2, 1 − √3i


## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s1 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 2 | s4 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 3 | s6 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 4 | s8 | algebra step is an equality | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 5 | s0 | uses the given number | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 6 | final | r = │z│ | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 7 | final | cos θ = a/r | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 8 | final | sin θ = b/r | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 9 | final | θ is the principal argument (−π < θ ≤ π) | ✅ PASS | θ = π |
| 10 | final | r(cos θ + i sin θ) gives back z | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 11 | final | exactly 3 roots | ✅ PASS | 3 roots listed |
| 12 | final | root 0: z^3 = w | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 13 | final | root 1: z^3 = w | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 14 | final | root 2: z^3 = w | ✅ PASS | simplify(before − after) = 0; constant values agree |
| 15 | final | roots are all different | ✅ PASS | no repeated roots |
| 16 | final | second method: numeric roots of zⁿ − w | ✅ PASS | every root matches a numeric root |
