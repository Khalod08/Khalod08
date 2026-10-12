# Verification report — `rref-sys-infinite-3x3`

- **Course / topic:** MATH1104 / row-reduction
- **Type:** rref
- **Generated:** 2026-09-30T21:10:05
- **Solution digest:** `66ec65610d4662a1`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 26 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Solve x₁ + 2x₂ − x₃ = 3, 2x₁ + 5x₂ + x₃ = 8, 3x₁ + 7x₂ = 11.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 2 | −1 | │ | 3 |
| 2 | 5 | 1 | │ | 8 |
| 3 | 7 | 0 | │ | 11 |

## Steps

**s0 — Write the matrix.** Start from the matrix exactly as given.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 2 | −1 | │ | 3 |
| 2 | 5 | 1 | │ | 8 |
| 3 | 7 | 0 | │ | 11 |

**s1 — R₂ → R₂ − 2R₁.** Create a zero below the leading 1 in column 1.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 2 | −1 | │ | 3 |
| 0 | 1 | 3 | │ | 2 |
| 3 | 7 | 0 | │ | 11 |

**s2 — R₃ → R₃ − 3R₁.** Create a zero below the leading 1 in column 1.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 2 | −1 | │ | 3 |
| 0 | 1 | 3 | │ | 2 |
| 0 | 1 | 3 | │ | 2 |

**s3 — R₃ → R₃ − R₂.** Create a zero below the leading 1 in column 2.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 2 | −1 | │ | 3 |
| 0 | 1 | 3 | │ | 2 |
| 0 | 0 | 0 | │ | 0 |

**s4 — R₁ → R₁ − 2R₂.** Create a zero above the leading 1 in column 2.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 0 | −7 | │ | −1 |
| 0 | 1 | 3 | │ | 2 |
| 0 | 0 | 0 | │ | 0 |

## Answer: RREF

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 0 | −7 | │ | −1 |
| 0 | 1 | 3 | │ | 2 |
| 0 | 0 | 0 | │ | 0 |

- Free variable(s): x₃. The system has infinitely many solutions.
- Solution: x₁ = 7t − 1, x₂ = 2 − 3t, x₃ = t  (t any real number)

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s0 | matches the given matrix | ✅ PASS | starting matrix is exactly the confirmed problem |
| 2 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 3 | s1 | elementary row operation | ✅ PASS | R₂ → R₂ − 2R₁ is valid (adding a multiple of a different row) |
| 4 | s1 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 5 | s1 | creates the intended zero | ✅ PASS | entry (2,1) is now 0 |
| 6 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 7 | s2 | elementary row operation | ✅ PASS | R₃ → R₃ − 3R₁ is valid (adding a multiple of a different row) |
| 8 | s2 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 9 | s2 | creates the intended zero | ✅ PASS | entry (3,1) is now 0 |
| 10 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 11 | s3 | elementary row operation | ✅ PASS | R₃ → R₃ − R₂ is valid (adding a multiple of a different row) |
| 12 | s3 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 13 | s3 | creates the intended zero | ✅ PASS | entry (3,2) is now 0 |
| 14 | s3 | forward phase reaches REF | ✅ PASS | row echelon form |
| 15 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 16 | s4 | elementary row operation | ✅ PASS | R₁ → R₁ − 2R₂ is valid (adding a multiple of a different row) |
| 17 | s4 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 18 | s4 | creates the intended zero | ✅ PASS | entry (1,2) is now 0 |
| 19 | final | result is in RREF | ✅ PASS | all four RREF conditions hold |
| 20 | final | second method: SymPy rref() | ✅ PASS | matches SymPy's independent rref() |
| 21 | final | rank by two methods | ✅ PASS | rank = 2 (pivot count = SymPy rank = NumPy SVD rank) |
| 22 | system | particular solution satisfies Ax = b | ✅ PASS | substituting back gives A·x = b exactly |
| 23 | system | direction vector 1 satisfies Av = 0 | ✅ PASS | A·v = 0 |
| 24 | system | general solution substituted back | ✅ PASS | A·x − b = 0 for every value of the parameters |
| 25 | system | number of free variables | ✅ PASS | 1 free variable(s) = n − rank(A) = 3 − 2 |
| 26 | system | second method: linsolve | ✅ PASS | linsolve's solution set matches (same particular solution, same free variables) |
