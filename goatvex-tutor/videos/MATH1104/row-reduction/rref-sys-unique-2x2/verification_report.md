# Verification report — `rref-sys-unique-2x2`

- **Course / topic:** MATH1104 / row-reduction
- **Type:** rref
- **Generated:** 2026-10-07T21:35:18
- **Solution digest:** `6700cab93dab55a1`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 24 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Solve 2x + 3y = 8, x − y = −1.

| x₁ | x₂ | │ | b |
| --- | --- | --- | --- |
| 2 | 3 | │ | 8 |
| 1 | −1 | │ | −1 |

## Steps

**s0 — Write the matrix.** Start from the matrix exactly as given.

| x₁ | x₂ | │ | b |
| --- | --- | --- | --- |
| 2 | 3 | │ | 8 |
| 1 | −1 | │ | −1 |

**s1 — R₁ ↔ R₂.** Swap rows to bring a leading 1 into the pivot position of column 1.

| x₁ | x₂ | │ | b |
| --- | --- | --- | --- |
| 1 | −1 | │ | −1 |
| 2 | 3 | │ | 8 |

**s2 — R₂ → R₂ − 2R₁.** Create a zero below the leading 1 in column 1.

| x₁ | x₂ | │ | b |
| --- | --- | --- | --- |
| 1 | −1 | │ | −1 |
| 0 | 5 | │ | 10 |

**s3 — R₂ → (1/5)R₂.** Scale row 2 so the pivot in column 2 becomes a leading 1.

| x₁ | x₂ | │ | b |
| --- | --- | --- | --- |
| 1 | −1 | │ | −1 |
| 0 | 1 | │ | 2 |

**s4 — R₁ → R₁ + R₂.** Create a zero above the leading 1 in column 2.

| x₁ | x₂ | │ | b |
| --- | --- | --- | --- |
| 1 | 0 | │ | 1 |
| 0 | 1 | │ | 2 |

## Answer: RREF

| x₁ | x₂ | │ | b |
| --- | --- | --- | --- |
| 1 | 0 | │ | 1 |
| 0 | 1 | │ | 2 |

- Every variable column has a pivot, so the system has exactly one solution.
- Solution: x₁ = 1, x₂ = 2

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s0 | matches the given matrix | ✅ PASS | starting matrix is exactly the confirmed problem |
| 2 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 3 | s1 | elementary row operation | ✅ PASS | R₁ ↔ R₂ is valid (swap of two different rows) |
| 4 | s1 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 5 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 6 | s2 | elementary row operation | ✅ PASS | R₂ → R₂ − 2R₁ is valid (adding a multiple of a different row) |
| 7 | s2 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 8 | s2 | creates the intended zero | ✅ PASS | entry (2,1) is now 0 |
| 9 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 10 | s3 | elementary row operation | ✅ PASS | R₂ → (1/5)R₂ is valid (scaling by the nonzero number 1/5) |
| 11 | s3 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 12 | s3 | creates a leading 1 | ✅ PASS | entry (2,2) is now 1 |
| 13 | s3 | forward phase reaches REF | ✅ PASS | row echelon form |
| 14 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 15 | s4 | elementary row operation | ✅ PASS | R₁ → R₁ + R₂ is valid (adding a multiple of a different row) |
| 16 | s4 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 17 | s4 | creates the intended zero | ✅ PASS | entry (1,2) is now 0 |
| 18 | final | result is in RREF | ✅ PASS | all four RREF conditions hold |
| 19 | final | second method: SymPy rref() | ✅ PASS | matches SymPy's independent rref() |
| 20 | final | rank by two methods | ✅ PASS | rank = 2 (pivot count = SymPy rank = NumPy SVD rank) |
| 21 | system | particular solution satisfies Ax = b | ✅ PASS | substituting back gives A·x = b exactly |
| 22 | system | general solution substituted back | ✅ PASS | A·x − b = 0 for every value of the parameters |
| 23 | system | number of free variables | ✅ PASS | 0 free variable(s) = n − rank(A) = 2 − 2 |
| 24 | system | second method: linsolve | ✅ PASS | linsolve's solution set matches (same particular solution, same free variables) |
