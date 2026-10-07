# Verification report — `inverse-2x2-det1`

- **Course / topic:** MATH1104 / matrix-inverse
- **Type:** matrix_inverse
- **Generated:** 2026-10-07T21:41:04
- **Solution digest:** `a97d33240361fbf8`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 24 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Find A⁻¹ if it exists.

|   |   |
| --- | --- |
| 2 | 1 |
| 5 | 3 |

## Steps

**s0 — Form [A | I].** Place the 2×2 identity matrix beside A. Row reducing the left half to I turns the right half into A⁻¹.

|   |   | │ |   |   |
| --- | --- | --- | --- | --- |
| 2 | 1 | │ | 1 | 0 |
| 5 | 3 | │ | 0 | 1 |

**s1 — R₁ → (1/2)R₁.** Scale row 1 so the pivot in column 1 becomes a leading 1.

|   |   | │ |   |   |
| --- | --- | --- | --- | --- |
| 1 | 1/2 | │ | 1/2 | 0 |
| 5 | 3 | │ | 0 | 1 |

**s2 — R₂ → R₂ − 5R₁.** Create a zero below the leading 1 in column 1.

|   |   | │ |   |   |
| --- | --- | --- | --- | --- |
| 1 | 1/2 | │ | 1/2 | 0 |
| 0 | 1/2 | │ | −5/2 | 1 |

**s3 — R₂ → 2R₂.** Scale row 2 so the pivot in column 2 becomes a leading 1.

|   |   | │ |   |   |
| --- | --- | --- | --- | --- |
| 1 | 1/2 | │ | 1/2 | 0 |
| 0 | 1 | │ | −5 | 2 |

**s4 — R₁ → R₁ − (1/2)R₂.** Create a zero above the leading 1 in column 2.

|   |   | │ |   |   |
| --- | --- | --- | --- | --- |
| 1 | 0 | │ | 3 | −1 |
| 0 | 1 | │ | −5 | 2 |

## Answer: A⁻¹

|   |   |
| --- | --- |
| 3 | −1 |
| −5 | 2 |

- The left half became I, so A is invertible and the right half is A⁻¹.

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s0 | matches the given matrix | ✅ PASS | A is exactly the confirmed problem |
| 2 | s0 | [A │ I] set up correctly | ✅ PASS | right half is the identity |
| 3 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 4 | s1 | elementary row operation | ✅ PASS | R₁ → (1/2)R₁ is valid (scaling by the nonzero number 1/2) |
| 5 | s1 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 6 | s1 | creates a leading 1 | ✅ PASS | entry (1,1) is now 1 |
| 7 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 8 | s2 | elementary row operation | ✅ PASS | R₂ → R₂ − 5R₁ is valid (adding a multiple of a different row) |
| 9 | s2 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 10 | s2 | creates the intended zero | ✅ PASS | entry (2,1) is now 0 |
| 11 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 12 | s3 | elementary row operation | ✅ PASS | R₂ → 2R₂ is valid (scaling by the nonzero number 2) |
| 13 | s3 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 14 | s3 | creates a leading 1 | ✅ PASS | entry (2,2) is now 1 |
| 15 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 16 | s4 | elementary row operation | ✅ PASS | R₁ → R₁ − (1/2)R₂ is valid (adding a multiple of a different row) |
| 17 | s4 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 18 | s4 | creates the intended zero | ✅ PASS | entry (1,2) is now 0 |
| 19 | final | determinant by two methods | ✅ PASS | det(A) = 1 (row reduction/Bareiss = cofactor expansion) |
| 20 | final | A·A⁻¹ = I | ✅ PASS | A·A⁻¹ = I exactly |
| 21 | final | A⁻¹·A = I | ✅ PASS | A⁻¹·A = I exactly |
| 22 | final | second method: adjugate formula | ✅ PASS | A⁻¹ = adj(A)/det(A) gives the same matrix |
| 23 | final | floating-point cross-check | ✅ PASS | NumPy's inverse agrees |
| 24 | final | determinant is nonzero | ✅ PASS | det(A) ≠ 0, consistent with invertible |
