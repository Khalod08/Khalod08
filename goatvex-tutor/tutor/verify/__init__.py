"""Step verifiers. ``verify(solution)`` runs every check for the problem type."""

from __future__ import annotations

from tutor.steps import Solution
from tutor.verify.result import FAIL, INCONCLUSIVE, PASS, CheckResult, overall


def verify(solution: Solution) -> list[CheckResult]:
    from tutor.verify.calculus import verify_derivative
    from tutor.verify.linear_algebra import verify_inverse, verify_rref

    by_type = {
        "rref": verify_rref,
        "matrix_inverse": verify_inverse,
        "derivative": verify_derivative,
    }
    fn = by_type.get(solution.problem.type)
    if fn is None:
        return [CheckResult("final", "verifier exists", FAIL, f"no verifier for type {solution.problem.type!r}")]
    try:
        return fn(solution)
    except Exception as exc:  # a crashing verifier must never look like a pass
        return [CheckResult("final", "verifier ran", FAIL, f"verifier crashed: {type(exc).__name__}: {exc}")]


__all__ = ["verify", "overall", "CheckResult", "PASS", "FAIL", "INCONCLUSIVE"]
