"""Step verifiers. ``verify(solution)`` runs every check for the problem type."""

from __future__ import annotations

from tutor.steps import Solution
from tutor.verify.result import FAIL, INCONCLUSIVE, PASS, CheckResult, overall


def verify(solution: Solution) -> list[CheckResult]:
    from tutor import registry

    types = registry.load_all()
    fn = types[solution.problem.type].verify if solution.problem.type in types else None
    if fn is None:
        return [CheckResult("final", "verifier exists", FAIL, f"no verifier for type {solution.problem.type!r}")]
    try:
        return fn(solution)
    except Exception as exc:  # a crashing verifier must never look like a pass
        return [CheckResult("final", "verifier ran", FAIL, f"verifier crashed: {type(exc).__name__}: {exc}")]


__all__ = ["verify", "overall", "CheckResult", "PASS", "FAIL", "INCONCLUSIVE"]
