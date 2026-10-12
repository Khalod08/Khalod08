# Verification report — `rref-sys-unique-3x3`

- **Course / topic:** MATH1104 / row-reduction
- **Type:** rref
- **Generated:** 2026-10-07T21:33:15
- **Solution digest:** `acec4842d8d20a45`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 37 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Solve x + y + z = 6, 2y + 5z = −4, 2x + 5y − z = 27.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 1 | │ | 6 |
| 0 | 2 | 5 | │ | −4 |
| 2 | 5 | −1 | │ | 27 |

## Steps

**s0 — Write the matrix.** Start from the matrix exactly as given.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 1 | │ | 6 |
| 0 | 2 | 5 | │ | −4 |
| 2 | 5 | −1 | │ | 27 |

**s1 — R₃ → R₃ − 2R₁.** Create a zero below the leading 1 in column 1.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 1 | │ | 6 |
| 0 | 2 | 5 | │ | −4 |
| 0 | 3 | −3 | │ | 15 |

**s2 — R₂ → (1/2)R₂.** Scale row 2 so the pivot in column 2 becomes a leading 1.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 1 | │ | 6 |
| 0 | 1 | 5/2 | │ | −2 |
| 0 | 3 | −3 | │ | 15 |

**s3 — R₃ → R₃ − 3R₂.** Create a zero below the leading 1 in column 2.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 1 | │ | 6 |
| 0 | 1 | 5/2 | │ | −2 |
| 0 | 0 | −21/2 | │ | 21 |

**s4 — R₃ → (−2/21)R₃.** Scale row 3 so the pivot in column 3 becomes a leading 1.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 1 | │ | 6 |
| 0 | 1 | 5/2 | │ | −2 |
| 0 | 0 | 1 | │ | −2 |

**s5 — R₁ → R₁ − R₃.** Create a zero above the leading 1 in column 3.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 0 | │ | 8 |
| 0 | 1 | 5/2 | │ | −2 |
| 0 | 0 | 1 | │ | −2 |

**s6 — R₂ → R₂ − (5/2)R₃.** Create a zero above the leading 1 in column 3.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 1 | 0 | │ | 8 |
| 0 | 1 | 0 | │ | 3 |
| 0 | 0 | 1 | │ | −2 |

**s7 — R₁ → R₁ − R₂.** Create a zero above the leading 1 in column 2.

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 0 | 0 | │ | 5 |
| 0 | 1 | 0 | │ | 3 |
| 0 | 0 | 1 | │ | −2 |

## Answer: RREF

| x₁ | x₂ | x₃ | │ | b |
| --- | --- | --- | --- | --- |
| 1 | 0 | 0 | │ | 5 |
| 0 | 1 | 0 | │ | 3 |
| 0 | 0 | 1 | │ | −2 |

- Every variable column has a pivot, so the system has exactly one solution.
- Solution: x₁ = 5, x₂ = 3, x₃ = −2

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s0 | matches the given matrix | ✅ PASS | starting matrix is exactly the confirmed problem |
| 2 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 3 | s1 | elementary row operation | ✅ PASS | R₃ → R₃ − 2R₁ is valid (adding a multiple of a different row) |
| 4 | s1 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 5 | s1 | creates the intended zero | ✅ PASS | entry (3,1) is now 0 |
| 6 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 7 | s2 | elementary row operation | ✅ PASS | R₂ → (1/2)R₂ is valid (scaling by the nonzero number 1/2) |
| 8 | s2 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 9 | s2 | creates a leading 1 | ✅ PASS | entry (2,2) is now 1 |
| 10 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 11 | s3 | elementary row operation | ✅ PASS | R₃ → R₃ − 3R₂ is valid (adding a multiple of a different row) |
| 12 | s3 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 13 | s3 | creates the intended zero | ✅ PASS | entry (3,2) is now 0 |
| 14 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 15 | s4 | elementary row operation | ✅ PASS | R₃ → (−2/21)R₃ is valid (scaling by the nonzero number −2/21) |
| 16 | s4 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 17 | s4 | creates a leading 1 | ✅ PASS | entry (3,3) is now 1 |
| 18 | s4 | forward phase reaches REF | ✅ PASS | row echelon form |
| 19 | s5 | continues from previous step | ✅ PASS | starts from the result of s4 |
| 20 | s5 | elementary row operation | ✅ PASS | R₁ → R₁ − R₃ is valid (adding a multiple of a different row) |
| 21 | s5 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 22 | s5 | creates the intended zero | ✅ PASS | entry (1,3) is now 0 |
| 23 | s6 | continues from previous step | ✅ PASS | starts from the result of s5 |
| 24 | s6 | elementary row operation | ✅ PASS | R₂ → R₂ − (5/2)R₃ is valid (adding a multiple of a different row) |
| 25 | s6 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 26 | s6 | creates the intended zero | ✅ PASS | entry (2,3) is now 0 |
| 27 | s7 | continues from previous step | ✅ PASS | starts from the result of s6 |
| 28 | s7 | elementary row operation | ✅ PASS | R₁ → R₁ − R₂ is valid (adding a multiple of a different row) |
| 29 | s7 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 30 | s7 | creates the intended zero | ✅ PASS | entry (1,2) is now 0 |
| 31 | final | result is in RREF | ✅ PASS | all four RREF conditions hold |
| 32 | final | second method: SymPy rref() | ✅ PASS | matches SymPy's independent rref() |
| 33 | final | rank by two methods | ✅ PASS | rank = 3 (pivot count = SymPy rank = NumPy SVD rank) |
| 34 | system | particular solution satisfies Ax = b | ✅ PASS | substituting back gives A·x = b exactly |
| 35 | system | general solution substituted back | ✅ PASS | A·x − b = 0 for every value of the parameters |
| 36 | system | number of free variables | ✅ PASS | 0 free variable(s) = n − rank(A) = 3 − 3 |
| 37 | system | second method: linsolve | ✅ PASS | linsolve's solution set matches (same particular solution, same free variables) |
