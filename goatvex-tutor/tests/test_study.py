"""Phase 4 study modes: hints, /check, progress + spaced repetition, practice, test prep, MC, write-ups."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest
import sympy as sp

from tutor import registry
from tutor.parse.schema import problem_from_dict
from tutor.pipeline import solve_problem
from tutor.student import progress
from tutor.study import plan
from tutor.study.check import check_attempt
from tutor.study.hints import ladder
from tutor.verify.equivalence import check_equal
from tutor.verify.result import FAIL


def solved(ptype, course="MATH1004", context=None, **given):
    p = problem_from_dict(dict(slug="t", course=course, type=ptype, given=given, confirmed_by_student=True,
                               context=context or {}))
    r = solve_problem(p)
    assert r.verified
    return r.solution


@pytest.fixture
def student(tmp_path, monkeypatch):
    """Point progress.json / sessions / tests at a temporary folder."""
    from tutor.study import practice, testprep

    monkeypatch.setattr(progress, "PROGRESS_FILE", tmp_path / "progress.json")
    monkeypatch.setattr(practice, "SESSIONS", tmp_path / "sessions")
    monkeypatch.setattr(testprep, "TESTS_DIR", tmp_path / "tests")
    monkeypatch.setenv("GOATVEX_NO_BROWSER", "1")
    return tmp_path


# ---------------------------------------------------------------- hints
def test_hint_ladder_reveals_verified_steps_in_order():
    sol = solved("derivative", function="sin(x^2)", variable="x")
    lad = ladder(sol)
    assert lad[0].title == "Strategy"
    assert lad[-1].title == "Answer" and "2x" in lad[-1].text.replace("·", "")
    assert [h.level for h in lad] == list(range(1, len(lad) + 1))
    assert "Chain rule" in " ".join(h.text for h in lad)


def test_graded_problem_hints_stop_before_the_answer():
    sol = solved("derivative", context={"graded": True}, function="x^2 sin(x)", variable="x")
    lad = ladder(sol)
    assert all(h.title != "Answer" for h in lad)
    assert "graded" in lad[-1].text


# ---------------------------------------------------------------- /check
@pytest.mark.parametrize("ptype,given,attempt,first_wrong,mistake", [
    ("derivative", {"function": "sin(x^2)", "variable": "x"}, "f'(x) = cos(x^2)", 1,
     "forgot chain rule inner derivative"),
    ("derivative", {"function": "x^2 sin(x)", "variable": "x"}, "= 2x cos(x)", 1, "product rule applied wrong"),
    ("derivative", {"function": "x^2/(x+1)", "variable": "x"}, "= (x^2 - 2x(x+1))/(x+1)^2", 1,
     "quotient rule order/sign"),
    ("derivative", {"function": "x^2 sin(x)", "variable": "x"}, "= 2x sin(x) - x^2 cos(x)", 1, "sign error"),
    ("derivative", {"function": "sin(x^2)", "variable": "x"}, "f'(x) = 2x cos(x^2)", None, None),
    ("indefinite_integral", {"integrand": "cos(3x)", "variable": "x"}, "= sin(3x)", 1,
     "forgot to divide by the inner derivative"),
    ("indefinite_integral", {"integrand": "x e^x", "variable": "x"}, "u = x, dv = e^x dx\n= x e^x - e^x + C", None,
     None),
    ("limit", {"function": "(x^2-4)/(x-2)", "variable": "x", "point": "2"}, "= (x-2)(x+2)/(x-2)\n= x + 2\n= 4",
     None, None),
    ("limit", {"function": "(x^2-4)/(x-2)", "variable": "x", "point": "2"}, "= x + 2\n= 5", 2, "arithmetic error"),
    ("definite_integral", {"integrand": "x^2", "variable": "x", "a": "0", "b": "2"}, "= x^3/3\n= -8/3", 2,
     "sign error"),
])
def test_check_finds_first_wrong_line(ptype, given, attempt, first_wrong, mistake):
    rep = check_attempt(solved(ptype, **given), attempt)
    assert rep.first_wrong == first_wrong, rep.text()
    if mistake:
        assert rep.mistake == mistake, rep.text()
    else:
        assert rep.final_correct, rep.text()


def test_check_row_reduction():
    sol = solved("rref", course="MATH1104", matrix=[["1", "2", "3"], ["2", "5", "8"]], augmented=True)
    good = check_attempt(sol, "1 2 3; 2 5 8\n1 2 3; 0 1 2\n1 0 -1; 0 1 2")
    assert good.first_wrong is None and good.final_correct
    assert "R₂ → R₂ − (2)R₁" in good.lines[1].detail
    sign = check_attempt(sol, "1 2 3; 2 5 8\n1 2 3; 0 9 14")
    assert sign.first_wrong == 2 and sign.mistake == "sign error in row reduction"
    arith = check_attempt(sol, "1 2 3; 2 5 8\n1 2 3; 0 1 3")
    assert arith.first_wrong == 2 and arith.mistake == "arithmetic error in a row operation"
    unfinished = check_attempt(sol, "1 2 3; 2 5 8\n1 2 3; 0 1 2")
    assert unfinished.first_wrong is None and unfinished.final_correct is False


def test_check_matrix_inverse_with_swap():
    sol = solved("matrix_inverse", course="MATH1104", matrix=[["2", "1"], ["1", "1"]])
    rep = check_attempt(sol, "2 1 1 0; 1 1 0 1\n1 1 0 1; 2 1 1 0\n1 1 0 1; 0 -1 1 -2\n1 1 0 1; 0 1 -1 2\n"
                             "1 0 1 -1; 0 1 -1 2")
    assert rep.first_wrong is None and rep.final_correct, rep.text()
    assert "↔" in rep.lines[1].detail


def test_graded_check_does_not_show_the_solution_step():
    sol = solved("derivative", context={"graded": True}, function="sin(x^2)", variable="x")
    rep = check_attempt(sol, "cos(x^2)")
    assert rep.mistake == "forgot chain rule inner derivative" and rep.compare_step == ""


# ---------------------------------------------------------------- progress / spaced repetition
def test_leitner_boxes_and_due_dates():
    data = progress.empty()
    d0 = date(2026, 10, 1)
    progress.record(data, "derivatives", True, "MATH1004", when=d0)
    progress.record(data, "derivatives", True, "MATH1004", when=d0)
    t = data["topics"]["derivatives"]
    assert t["box"] == 2 and t["next_review"] == (d0 + timedelta(days=progress.INTERVALS[2])).isoformat()
    progress.record(data, "derivatives", False, "MATH1004", mistake="sign error", when=d0)
    assert data["topics"]["derivatives"]["box"] == 0
    assert progress.due(data, d0 + timedelta(days=1))[0][0] == "derivatives"
    progress.record(data, "limits", True, "MATH1004", when=d0)
    weak = progress.weak_topics(data)
    assert weak[0].topic == "derivatives"
    w = progress.topic_weights(data, ["derivatives", "limits", "integrals"])
    assert w["derivatives"] > w["limits"]
    assert progress.mistake_counts(data)["sign error"] == 1


def test_progress_file_roundtrip(student):
    data = progress.load()
    progress.record(data, "row-reduction", True, "MATH1104")
    progress.save(data)
    assert progress.load()["topics"]["row-reduction"]["correct"] == 1


# ---------------------------------------------------------------- course plan
def test_test_coverage_from_the_course_plan():
    t1 = plan.find_test("MATH1004", "test1")
    specs = plan.covered_specs("MATH1004", t1.date)
    assert "limit" in specs and "derivative" in specs
    assert "optimization" not in specs  # week 5 starts on the test day
    t2 = plan.find_test("MATH1104", "Test 2")
    assert {"matrix_inverse", "determinant", "cramers_rule", "rref"} <= set(plan.covered_specs("MATH1104", t2.date))
    for c in plan.COURSES:
        for w in plan.weeks(c):
            for spec in w.get("goatvex_types", []):
                name, _, variant = spec.partition(":")
                pt = registry.get(name)
                assert variant == "" or variant in pt.variants, spec


@pytest.mark.parametrize("spec", sorted({s for c in plan.COURSES for w in plan.weeks(c)
                                         for s in w.get("goatvex_types", []) if ":" in s}))
def test_every_variant_generates_verified_problems(spec):
    from tutor.study.generate import verified_problem

    for seed in range(3):
        p, res = verified_problem(spec, random.Random(seed), 2, tries=3)
        assert res.verified


# ---------------------------------------------------------------- practice + test prep
def test_practice_session_grades_and_records(student):
    from tutor.study import practice as P

    s = P.new_session("practice", "MATH1004", n=2, specs=["derivative", "limit"], seed=1)
    assert len(s["items"]) == 2 and all(it["result"] is None for it in s["items"])
    it = P.grade_item(s, 1, s["items"][0]["answer"])
    assert it["result"]["correct"] is True
    it = P.grade_item(P.load_session(s["id"]), 2, "12345")
    assert it["result"]["correct"] is False
    q = P.finish_quiz(P.load_session(s["id"]))
    assert (q["score"], q["total"]) == (1, 2)
    data = progress.load()
    assert data["topics"]["derivatives"]["correct"] == 1 and data["topics"]["limits"]["wrong"] == 1


def test_testprep_builds_and_grades(student):
    from tutor.study import testprep as T

    s = T.build("MATH1104", "test2", n=4, seed=2)
    allowed = set(plan.covered_specs("MATH1104", plan.find_test("MATH1104", "test2").date))
    assert all(it["spec"] in allowed for it in s["items"])
    assert (student / "tests" / s["id"] / "test.html").exists()
    answers = [s["items"][0]["answer"], "0", "", s["items"][3]["answer"]]
    g = T.grade(s["id"], answers, make_writeups=False)
    assert g["score"]["total"] == 4 and g["score"]["score"] >= 2
    html = (student / "tests" / s["id"] / "report.html").read_text(encoding="utf-8")
    assert "What to review" in html


def test_multiple_choice_distractors_are_proven_wrong():
    from tutor.study.choices import choices

    sol = solved("indefinite_integral", integrand="cos(x)", variable="x")
    mc = choices(sol, random.Random(0))
    assert mc and len(mc["choices"]) == 4
    x = sp.Symbol("x", real=True)
    right = [c for c in mc["choices"] if c["letter"] == mc["correct_choice"]]
    assert len(right) == 1
    from tutor.types._answers import parse_answer_expr

    for c in mc["choices"]:
        if c["letter"] != mc["correct_choice"]:
            e = parse_answer_expr(c["text"], ["x"]).subs(sp.Symbol("x"), x)
            assert check_equal(sp.diff(e, x), sp.cos(x), [x])[0] == FAIL  # not secretly an antiderivative


# ---------------------------------------------------------------- write-ups + explain
def test_writeup_page(tmp_path):
    from tutor.pipeline import run
    from tutor.writeup.html import write_solution

    p = problem_from_dict(dict(slug="w", course="MATH1104", type="determinant",
                               given={"matrix": [["2", "1"], ["1", "3"]]}, confirmed_by_student=True))
    r = run(p, out_dir=tmp_path / "w")
    path = write_solution(r, practice=False)
    html = path.read_text(encoding="utf-8")
    assert "katex" in html and "Verified" in html and "Step by step" in html
    assert "\\left[\\begin{matrix}" in html or "begin{matrix}" in html


def test_writeup_refuses_unverified(tmp_path):
    from dataclasses import replace

    from tutor.pipeline import run
    from tutor.writeup.html import write_solution

    p = problem_from_dict(dict(slug="w", course="MATH1104", type="determinant",
                               given={"matrix": [["2", "1"], ["1", "3"]]}, confirmed_by_student=True))
    r = run(p, out_dir=tmp_path / "w")
    with pytest.raises(ValueError):
        write_solution(replace(r, status=FAIL), practice=False)


@pytest.mark.parametrize("query,expected", [("chain rule", "derivative"), ("eigenvalues of a matrix", "eigen"),
                                            ("integration by parts", "indefinite_integral"),
                                            ("Gram-Schmidt", "orthogonality"), ("L'Hôpital limit", "limit")])
def test_explain_matches_concepts(query, expected):
    from tutor.study.explain import match

    assert match(query)[0][0] == expected
