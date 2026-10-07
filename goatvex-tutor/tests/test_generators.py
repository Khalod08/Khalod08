"""Every practice-problem generator must produce problems that solve and fully verify."""

from __future__ import annotations

import random

import pytest

from tutor import registry
from tutor.parse.schema import problem_from_dict
from tutor.pipeline import solve_problem
from tutor.verify import PASS

TYPES = [t for t in registry.names() if registry.get(t).generate]


@pytest.mark.parametrize("ptype", TYPES)
@pytest.mark.parametrize("difficulty", [1, 2, 3])
def test_generated_problems_verify(ptype, difficulty):
    pt = registry.get(ptype)
    for seed in range(4):
        given, statement = pt.generate(random.Random(1000 * difficulty + seed), difficulty)
        p = problem_from_dict(dict(slug="practice", course=pt.course, type=ptype, given=given,
                                   statement=statement, confirmed_by_student=True))
        result = solve_problem(p)
        bad = [f"{c.step_id} {c.check}: {c.detail}" for c in result.checks if c.status != PASS]
        assert result.status == PASS, f"seed {seed}: {given}\n" + "\n".join(bad)


@pytest.mark.parametrize("ptype", TYPES)
def test_grader_accepts_the_verified_answer(ptype):
    """Typing the verified answer back must be graded correct (where auto-grading applies)."""
    from tutor.text.unicode_math import to_text

    pt = registry.get(ptype)
    if not pt.grade:
        pytest.skip("no grader")
    given, _ = pt.generate(random.Random(7), 2)
    p = problem_from_dict(dict(slug="practice", course=pt.course, type=ptype, given=given, confirmed_by_student=True))
    sol = solve_problem(p).solution
    ans = sol.answer
    if hasattr(ans, "rows") and ans.cols > 1:
        text = "; ".join(" ".join(str(ans[i, j]) for j in range(ans.cols)) for i in range(ans.rows))
    elif hasattr(ans, "rows") or isinstance(ans, list):
        text = ", ".join(str(a) for a in ans)
    else:
        text = str(ans)
    if isinstance(ans, list) and ans and hasattr(ans[0], "lhs"):
        pytest.skip("equation answers are compared in the write-up")
    if hasattr(ans, "lhs") and hasattr(ans, "rhs"):  # a line y = mx + b: the student types the right side
        text = str(ans.rhs)
    text = text.replace("y(x)", "y")
    if ptype == "complex" and sol.facts["task"] == "polar":
        text = f"{sol.facts['r']}, {sol.facts['theta']}"
    if ptype == "rref" and sol.facts["system"]["status"] != "unique":
        text = "; ".join(" ".join(str(ans[i, j]) for j in range(ans.cols)) for i in range(ans.rows))
    ok, msg = pt.grade(sol, text.replace("I", "i").replace("**", "^"))
    assert ok, f"{ptype}: {text!r} → {msg} (answer {to_text(ans)})"
