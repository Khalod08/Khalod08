"""Building blocks shared by every verifier.

Step kinds handled generically by :func:`verify_steps`:

- ``algebra``: ``before`` and ``after`` must be equal (expressions, numbers, or
  matrices entry by entry; symbolic proof + ≥5 numeric points).
- ``equation``: ``before``/``after`` are equations (or lists of equations); they
  must have the same solutions for ``data["unknowns"]``.
- ``row_op`` / ``derivative_rule`` / ``integral_rule``: the dedicated checkers.
- ``setup`` / ``fact``: no automatic check; the type's verifier checks them.

Each step may set ``data["chain"] = False`` when it does not continue from the
previous step (e.g. a side computation); otherwise every step must start
exactly where the previous one ended.
"""

from __future__ import annotations

from typing import Iterable

import sympy as sp

from tutor.steps import ALGEBRA, DERIVATIVE_RULE, EQUATION, FACT, INTEGRAL_RULE, ROW_OP, Solution, Step
from tutor.text.unicode_math import to_text
from tutor.verify.equivalence import check_equal
from tutor.verify.result import FAIL, INCONCLUSIVE, PASS, CheckResult

__all__ = ["EQUATION", "FACT", "INTEGRAL_RULE", "ok", "equal", "same_solutions", "chain_checks", "verify_steps"]


def ok(step_id: str, check: str, cond: bool, good: str, bad: str | None = None) -> CheckResult:
    return CheckResult(step_id, check, PASS if cond else FAIL, good if cond else (bad or f"NOT: {good}"))


def equal(step_id: str, check: str, a, b, symbols=None) -> CheckResult:
    """a = b for expressions, numbers or matrices (entrywise)."""
    a, b = _explicit(a), _explicit(b)
    if isinstance(a, sp.MatrixBase) or isinstance(b, sp.MatrixBase):
        if not (isinstance(a, sp.MatrixBase) and isinstance(b, sp.MatrixBase)) or a.shape != b.shape:
            return CheckResult(step_id, check, FAIL, "shapes differ")
        worst = PASS
        for i in range(a.rows):
            for j in range(a.cols):
                st, det = check_equal(a[i, j], b[i, j], symbols)
                if st == FAIL:
                    return CheckResult(step_id, check, FAIL, f"entry ({i + 1},{j + 1}): {det}")
                if st == INCONCLUSIVE:
                    worst = INCONCLUSIVE
        return CheckResult(step_id, check, worst, "equal entry by entry" if worst == PASS else "some entries unproven")
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        a, b = list(a), list(b)
        if len(a) != len(b):
            return CheckResult(step_id, check, FAIL, f"{len(a)} values vs {len(b)}")
        for k, (u, v) in enumerate(zip(a, b), 1):
            st, det = check_equal(u, v, symbols)
            if st != PASS:
                return CheckResult(step_id, check, st, f"item {k}: {det}")
        return CheckResult(step_id, check, PASS, "all values equal")
    st, det = check_equal(a, b, symbols)
    return CheckResult(step_id, check, st, det)


def _explicit(x):
    """Unevaluated matrix expressions of explicit matrices (A·B, Aᵀ) → their value via SymPy."""
    if isinstance(x, sp.MatrixExpr) and not isinstance(x, sp.MatrixBase):
        return sp.ImmutableMatrix(x.doit())
    return x


def same_solutions(step_id: str, check: str, eqs_a, eqs_b, unknowns) -> CheckResult:
    """Two equations/systems have the same solution set for ``unknowns``."""
    eqs_a = eqs_a if isinstance(eqs_a, (list, tuple)) else [eqs_a]
    eqs_b = eqs_b if isinstance(eqs_b, (list, tuple)) else [eqs_b]
    unknowns = list(unknowns)
    try:
        sa = sp.solve(list(eqs_a), unknowns, dict=True)
        sb = sp.solve(list(eqs_b), unknowns, dict=True)
    except Exception as exc:
        return CheckResult(step_id, check, INCONCLUSIVE, f"SymPy could not solve: {exc}")
    if len(sa) != len(sb):
        return CheckResult(step_id, check, FAIL, f"{len(sa)} solution(s) before, {len(sb)} after")
    remaining = list(sb)
    for s in sa:
        match = None
        for t in remaining:
            if set(s) == set(t) and all(check_equal(s[k], t[k])[0] == PASS for k in s):
                match = t
                break
        if match is None:
            return CheckResult(step_id, check, FAIL, f"solution {to_text(list(s.values()))} is not a solution after the step")
        remaining.remove(match)
    return CheckResult(step_id, check, PASS, "same solution(s) before and after")


def chain_checks(solution: Solution) -> list[CheckResult]:
    out = []
    steps = solution.steps
    for prev, cur in zip(steps, steps[1:]):
        if not cur.data.get("chain", True):
            continue
        same = _same(prev.after, cur.before)
        out.append(ok(cur.id, "continues from previous step", same, f"starts from the result of {prev.id}",
                      f"does not start from the result of {prev.id}"))
    return out


def _same(a, b) -> bool:
    if isinstance(a, sp.MatrixBase) and isinstance(b, sp.MatrixBase):
        return a.shape == b.shape and a == b
    try:
        return a == b
    except Exception:
        return False


def algebra_check(step: Step, symbols=None) -> CheckResult:
    return equal(step.id, "algebra step is an equality", step.before, step.after, symbols)


def verify_steps(solution: Solution, symbols: Iterable[sp.Symbol] | None = None) -> list[CheckResult]:
    """Chain + generic per-step checks for every step kind that has one."""
    symbols = list(symbols) if symbols is not None else None
    out = chain_checks(solution)
    for s in solution.steps:
        if s.kind == ALGEBRA:
            out.append(equal(s.id, "algebra step is an equality", s.before, s.after,
                             s.data.get("symbols", symbols)))
        elif s.kind == EQUATION:
            out.append(same_solutions(s.id, "equation step keeps the same solutions", s.before, s.after,
                                      s.data["unknowns"]))
        elif s.kind == ROW_OP:
            from tutor.verify.linear_algebra import check_row_op_step

            out += check_row_op_step(s)
        elif s.kind == DERIVATIVE_RULE:
            from tutor.verify.calculus import check_rule_step

            out += check_rule_step(s, s.data.get("variable") or symbols[0])
        elif s.kind == INTEGRAL_RULE:
            from tutor.verify.integrals import check_integral_step

            out += check_integral_step(s)
    return out
