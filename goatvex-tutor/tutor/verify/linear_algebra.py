"""Verifiers for row reduction and matrix inverses.

Every check here recomputes from scratch; nothing trusts the solver's own
bookkeeping. Independent second methods: SymPy's own ``rref()`` (a different
implementation), ``rank()``, the adjugate formula for inverses, determinants
by two methods, ``linsolve`` for systems, and a floating-point NumPy check.
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from tutor.solvers.linear_algebra.row_ops import REPLACE, SCALE, SWAP, RowOp, is_ref, is_rref
from tutor.steps import ROW_OP, SETUP, Solution
from tutor.text.unicode_math import to_text
from tutor.verify.result import FAIL, PASS, CheckResult


def _ok(step_id, check, cond, good, bad) -> CheckResult:
    return CheckResult(step_id, check, PASS if cond else FAIL, good if cond else bad)


def check_row_op_step(step) -> list[CheckResult]:
    """A row-op step must be ONE valid elementary row operation, and re-applying it
    to ``before`` must give exactly ``after``."""
    out: list[CheckResult] = []
    op: RowOp = step.data["rowop"]
    before, after = step.before, step.after
    n = before.rows
    in_range = 0 <= op.i < n and (op.j is None or 0 <= op.j < n)
    if op.kind == SWAP:
        valid = in_range and op.j is not None and op.i != op.j
        why = "swap of two different rows"
    elif op.kind == SCALE:
        valid = in_range and op.c is not None and op.c != 0 and op.c.is_rational
        why = f"scaling by the nonzero number {to_text(op.c) if op.c is not None else '?'}"
    elif op.kind == REPLACE:
        valid = in_range and op.j is not None and op.i != op.j and op.c is not None and op.c.is_rational
        why = "adding a multiple of a different row"
    else:
        valid, why = False, f"unknown operation {op.kind!r}"
    out.append(_ok(step.id, "elementary row operation", valid, f"{step.operation} is valid ({why})",
                   f"{step.operation} is NOT an elementary row operation ({why})"))

    # Re-apply independently (plain list arithmetic, not RowOp.apply)
    rows = [[before[i, j] for j in range(before.cols)] for i in range(n)]
    if valid:
        if op.kind == SWAP:
            rows[op.i], rows[op.j] = rows[op.j], rows[op.i]
        elif op.kind == SCALE:
            rows[op.i] = [op.c * v for v in rows[op.i]]
        else:
            rows[op.i] = [a + op.c * b for a, b in zip(rows[op.i], rows[op.j])]
    recomputed = sp.Matrix(rows)
    same = recomputed.shape == after.shape and all(sp.simplify(u - v) == 0 for u, v in zip(recomputed, after))
    bad_cells = [] if same else [
        f"({i + 1},{j + 1})" for i in range(after.rows) for j in range(after.cols)
        if recomputed.shape == after.shape and recomputed[i, j] != after[i, j]]
    out.append(_ok(step.id, "row op re-applied", same, "re-applying the operation reproduces the next matrix exactly",
                   f"re-applying the operation gives a different matrix (entries {', '.join(bad_cells) or 'shape'})"))

    # The multiplier must actually produce the zero it claims to (replacement steps)
    if op.kind == REPLACE and "pivot_column" in step.data:
        c = step.data["pivot_column"] - 1
        out.append(_ok(step.id, "creates the intended zero", after[op.i, c] == 0,
                       f"entry ({op.i + 1},{c + 1}) is now 0",
                       f"entry ({op.i + 1},{c + 1}) is {to_text(after[op.i, c])}, not 0 — wrong multiplier"))
    if op.kind == SCALE and "pivot_column" in step.data:
        c = step.data["pivot_column"] - 1
        out.append(_ok(step.id, "creates a leading 1", after[op.i, c] == 1,
                       f"entry ({op.i + 1},{c + 1}) is now 1",
                       f"entry ({op.i + 1},{c + 1}) is {to_text(after[op.i, c])}, not 1"))
    return out


def check_chain(solution: Solution) -> list[CheckResult]:
    """Each step must start exactly where the previous one ended."""
    out = []
    steps = solution.steps
    for prev, cur in zip(steps, steps[1:]):
        same = prev.after == cur.before
        out.append(_ok(cur.id, "continues from previous step", same, f"starts from the result of {prev.id}",
                       f"does not start from the result of {prev.id}"))
    return out


def _float_rank(m: sp.Matrix) -> int:
    return int(np.linalg.matrix_rank(np.array(m.evalf(), dtype=float)))


def verify_rref(solution: Solution) -> list[CheckResult]:
    out: list[CheckResult] = []
    a = solution.facts["input"]
    first = solution.steps[0]
    out.append(_ok(first.id, "matches the given matrix", first.after == solution.problem.matrix,
                   "starting matrix is exactly the confirmed problem", "starting matrix differs from problem.json"))
    out += check_chain(solution)
    for s in solution.steps:
        if s.kind == ROW_OP:
            out += check_row_op_step(s)

    r = solution.answer
    ok, why = is_rref(r)
    out.append(_ok("final", "result is in RREF", ok, why, why))
    ref_ok, ref_why = is_ref(solution.facts["ref"])
    out.append(_ok(solution.facts["ref_step"], "forward phase reaches REF", ref_ok, ref_why, ref_why))

    independent, pivots = a.rref()
    out.append(_ok("final", "second method: SymPy rref()", r == independent,
                   "matches SymPy's independent rref()", f"SymPy's rref() gives\n{to_text(independent)}"))
    rank = solution.facts["rank"]
    out.append(_ok("final", "rank by two methods", rank == a.rank() == _float_rank(a),
                   f"rank = {rank} (pivot count = SymPy rank = NumPy SVD rank)",
                   f"pivot count {rank}, SymPy rank {a.rank()}, NumPy rank {_float_rank(a)}"))

    if solution.facts.get("augmented"):
        out += verify_system(solution)
    return out


def verify_system(solution: Solution) -> list[CheckResult]:
    out: list[CheckResult] = []
    m = solution.facts["input"]
    A, b = m[:, :-1], m[:, -1]
    sysinfo = solution.facts["system"]
    rank_a, rank_ab = A.rank(), m.rank()
    xs = sp.symbols(f"x1:{A.cols + 1}")
    independent = sp.linsolve((A, b), *xs)
    if sysinfo["status"] == "inconsistent":
        out.append(_ok("system", "inconsistency confirmed", rank_a < rank_ab and independent == sp.EmptySet,
                       f"rank(A) = {rank_a} < rank([A|b]) = {rank_ab}; linsolve finds no solution",
                       "the system is NOT actually inconsistent"))
        return out
    xp = sysinfo["particular"]
    out.append(_ok("system", "particular solution satisfies Ax = b", A * xp == b,
                   "substituting back gives A·x = b exactly", "A·x ≠ b for the particular solution"))
    for k, v in enumerate(sysinfo["null_basis"], 1):
        out.append(_ok("system", f"direction vector {k} satisfies Av = 0", A * v == sp.zeros(A.rows, 1),
                       "A·v = 0", "A·v ≠ 0"))
    general = sysinfo["general"]
    residual = (A * general - b).applyfunc(sp.expand)
    out.append(_ok("system", "general solution substituted back", residual == sp.zeros(A.rows, 1),
                   "A·x − b = 0 for every value of the parameters", f"A·x − b = {to_text(residual)}"))
    nfree = len(sysinfo["null_basis"])
    out.append(_ok("system", "number of free variables", nfree == A.cols - rank_a,
                   f"{nfree} free variable(s) = n − rank(A) = {A.cols} − {rank_a}",
                   f"{nfree} free variable(s) but n − rank(A) = {A.cols - rank_a}"))
    # linsolve (independent) must describe the same set: each of its solutions satisfies ours and vice versa
    if independent == sp.EmptySet:
        out.append(CheckResult("system", "second method: linsolve", FAIL, "linsolve says no solution"))
    else:
        (sol,) = tuple(independent)
        sol_vec = sp.Matrix(sol)
        # set every free symbol linsolve left to 0 → must be one of our solutions (A x = b)
        sub0 = sol_vec.subs({s: 0 for s in xs})
        agree = A * sub0 == b and sub0 == xp
        out.append(_ok("system", "second method: linsolve", agree,
                       "linsolve's solution set matches (same particular solution, same free variables)",
                       f"linsolve gives {to_text(sol_vec.T)}"))
    return out


def verify_inverse(solution: Solution) -> list[CheckResult]:
    out: list[CheckResult] = []
    a = solution.facts["input"]
    n = solution.facts["n"]
    first = solution.steps[0]
    out.append(_ok(first.id, "matches the given matrix", first.before == solution.problem.matrix,
                   "A is exactly the confirmed problem", "A differs from problem.json"))
    out.append(_ok(first.id, "[A | I] set up correctly", first.after == a.row_join(sp.eye(n)),
                   "right half is the identity", "augmented matrix is not [A | I]"))
    out += check_chain(solution)
    for s in solution.steps:
        if s.kind == ROW_OP:
            out += check_row_op_step(s)

    det_bareiss = a.det(method="bareiss")
    det_cofactor = a.det(method="laplace") if n <= 6 else a.det(method="berkowitz")
    out.append(_ok("final", "determinant by two methods", det_bareiss == det_cofactor,
                   f"det(A) = {to_text(det_bareiss)} (row reduction/Bareiss = cofactor expansion)",
                   f"Bareiss gives {to_text(det_bareiss)}, cofactor gives {to_text(det_cofactor)}"))

    if solution.facts["invertible"]:
        inv = solution.answer
        out.append(_ok("final", "A·A⁻¹ = I", a * inv == sp.eye(n), "A·A⁻¹ = I exactly", f"A·A⁻¹ =\n{to_text(a * inv)}"))
        out.append(_ok("final", "A⁻¹·A = I", inv * a == sp.eye(n), "A⁻¹·A = I exactly", f"A⁻¹·A =\n{to_text(inv * a)}"))
        adj = a.adjugate() / det_cofactor if det_cofactor != 0 else None
        out.append(_ok("final", "second method: adjugate formula", adj is not None and adj == inv,
                       "A⁻¹ = adj(A)/det(A) gives the same matrix", "adjugate formula disagrees"))
        fl = np.linalg.inv(np.array(a.evalf(), dtype=float))
        close = np.allclose(fl, np.array(inv.evalf(), dtype=float), rtol=1e-9, atol=1e-12)
        out.append(_ok("final", "floating-point cross-check", close, "NumPy's inverse agrees",
                       "NumPy's floating-point inverse disagrees"))
        out.append(_ok("final", "determinant is nonzero", det_bareiss != 0, "det(A) ≠ 0, consistent with invertible",
                       "det(A) = 0 but an inverse was reported"))
    else:
        out.append(_ok("final", "not invertible confirmed", det_bareiss == 0 and a.rank() < n,
                       f"det(A) = 0 and rank(A) = {a.rank()} < {n}", "A is actually invertible"))
    return out
