# Verification report — `inverse-3x3-lay-b-swap`

- **Course / topic:** MATH1104 / matrix-inverse
- **Type:** matrix_inverse
- **Generated:** 2026-09-30T21:10:06
- **Solution digest:** `934d8ba01417ae4d`
- **Result:** ✅ PASS — **ALL CHECKS PASSED** — this solution may be rendered.
- **Checks:** 31 passed, 0 failed, 0 inconclusive

## Problem (as confirmed)

Find A⁻¹ if it exists.

|   |   |   |
| --- | --- | --- |
| 0 | 1 | 2 |
| 1 | 0 | 3 |
| 4 | −3 | 8 |

## Steps

**s0 — Form [A | I].** Place the 3×3 identity matrix beside A. Row reducing the left half to I turns the right half into A⁻¹.

|   |   |   | │ |   |   |   |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 1 | 2 | │ | 1 | 0 | 0 |
| 1 | 0 | 3 | │ | 0 | 1 | 0 |
| 4 | −3 | 8 | │ | 0 | 0 | 1 |

**s1 — R₁ ↔ R₂.** Swap rows to bring a leading 1 into the pivot position of column 1.

|   |   |   | │ |   |   |   |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 3 | │ | 0 | 1 | 0 |
| 0 | 1 | 2 | │ | 1 | 0 | 0 |
| 4 | −3 | 8 | │ | 0 | 0 | 1 |

**s2 — R₃ → R₃ − 4R₁.** Create a zero below the leading 1 in column 1.

|   |   |   | │ |   |   |   |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 3 | │ | 0 | 1 | 0 |
| 0 | 1 | 2 | │ | 1 | 0 | 0 |
| 0 | −3 | −4 | │ | 0 | −4 | 1 |

**s3 — R₃ → R₃ + 3R₂.** Create a zero below the leading 1 in column 2.

|   |   |   | │ |   |   |   |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 3 | │ | 0 | 1 | 0 |
| 0 | 1 | 2 | │ | 1 | 0 | 0 |
| 0 | 0 | 2 | │ | 3 | −4 | 1 |

**s4 — R₃ → (1/2)R₃.** Scale row 3 so the pivot in column 3 becomes a leading 1.

|   |   |   | │ |   |   |   |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 3 | │ | 0 | 1 | 0 |
| 0 | 1 | 2 | │ | 1 | 0 | 0 |
| 0 | 0 | 1 | │ | 3/2 | −2 | 1/2 |

**s5 — R₁ → R₁ − 3R₃.** Create a zero above the leading 1 in column 3.

|   |   |   | │ |   |   |   |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 0 | │ | −9/2 | 7 | −3/2 |
| 0 | 1 | 2 | │ | 1 | 0 | 0 |
| 0 | 0 | 1 | │ | 3/2 | −2 | 1/2 |

**s6 — R₂ → R₂ − 2R₃.** Create a zero above the leading 1 in column 3.

|   |   |   | │ |   |   |   |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 0 | │ | −9/2 | 7 | −3/2 |
| 0 | 1 | 0 | │ | −2 | 4 | −1 |
| 0 | 0 | 1 | │ | 3/2 | −2 | 1/2 |

## Answer: A⁻¹

|   |   |   |
| --- | --- | --- |
| −9/2 | 7 | −3/2 |
| −2 | 4 | −1 |
| 3/2 | −2 | 1/2 |

- The left half became I, so A is invertible and the right half is A⁻¹.

## Checks

| # | Step | Check | Result | Details |
|---|---|---|---|---|
| 1 | s0 | matches the given matrix | ✅ PASS | A is exactly the confirmed problem |
| 2 | s0 | [A │ I] set up correctly | ✅ PASS | right half is the identity |
| 3 | s1 | continues from previous step | ✅ PASS | starts from the result of s0 |
| 4 | s1 | elementary row operation | ✅ PASS | R₁ ↔ R₂ is valid (swap of two different rows) |
| 5 | s1 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 6 | s2 | continues from previous step | ✅ PASS | starts from the result of s1 |
| 7 | s2 | elementary row operation | ✅ PASS | R₃ → R₃ − 4R₁ is valid (adding a multiple of a different row) |
| 8 | s2 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 9 | s2 | creates the intended zero | ✅ PASS | entry (3,1) is now 0 |
| 10 | s3 | continues from previous step | ✅ PASS | starts from the result of s2 |
| 11 | s3 | elementary row operation | ✅ PASS | R₃ → R₃ + 3R₂ is valid (adding a multiple of a different row) |
| 12 | s3 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 13 | s3 | creates the intended zero | ✅ PASS | entry (3,2) is now 0 |
| 14 | s4 | continues from previous step | ✅ PASS | starts from the result of s3 |
| 15 | s4 | elementary row operation | ✅ PASS | R₃ → (1/2)R₃ is valid (scaling by the nonzero number 1/2) |
| 16 | s4 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 17 | s4 | creates a leading 1 | ✅ PASS | entry (3,3) is now 1 |
| 18 | s5 | continues from previous step | ✅ PASS | starts from the result of s4 |
| 19 | s5 | elementary row operation | ✅ PASS | R₁ → R₁ − 3R₃ is valid (adding a multiple of a different row) |
| 20 | s5 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 21 | s5 | creates the intended zero | ✅ PASS | entry (1,3) is now 0 |
| 22 | s6 | continues from previous step | ✅ PASS | starts from the result of s5 |
| 23 | s6 | elementary row operation | ✅ PASS | R₂ → R₂ − 2R₃ is valid (adding a multiple of a different row) |
| 24 | s6 | row op re-applied | ✅ PASS | re-applying the operation reproduces the next matrix exactly |
| 25 | s6 | creates the intended zero | ✅ PASS | entry (2,3) is now 0 |
| 26 | final | determinant by two methods | ✅ PASS | det(A) = −2 (row reduction/Bareiss = cofactor expansion) |
| 27 | final | A·A⁻¹ = I | ✅ PASS | A·A⁻¹ = I exactly |
| 28 | final | A⁻¹·A = I | ✅ PASS | A⁻¹·A = I exactly |
| 29 | final | second method: adjugate formula | ✅ PASS | A⁻¹ = adj(A)/det(A) gives the same matrix |
| 30 | final | floating-point cross-check | ✅ PASS | NumPy's inverse agrees |
| 31 | final | determinant is nonzero | ✅ PASS | det(A) ≠ 0, consistent with invertible |
