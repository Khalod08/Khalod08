"""Narration: spoken math, the no-math-outside-placeholders lint, and caption chunks."""

from __future__ import annotations

from pathlib import Path

import pytest
import sympy as sp

from tutor.narration import generic
from tutor.narration.script import N, OP, Line, V, lint_template
from tutor.narration.scripts import row_reduction
from tutor.narration.spoken import number_words, say, say_row_op
from tutor.parse.schema import load_problem
from tutor.pipeline import solve_problem
from tutor.solvers.linear_algebra.row_ops import REPLACE, SCALE, RowOp
from tutor.video.base import caption_chunks

BENCH = sorted((Path(__file__).parent / "benchmark").rglob("*.json"))


def test_spoken_numbers_and_expressions():
    x = sp.Symbol("x")
    assert number_words(sp.Rational(-3, 2)) == "negative three halves"
    assert number_words(sp.Rational(1, 3)) == "one third"
    assert number_words(27) == "twenty-seven"
    assert say(3 * x**2 + 1) == "three x squared plus one"
    assert say_row_op(RowOp(REPLACE, 1, 0, sp.Integer(-3))) == "replace row two with row two minus three times row one"
    assert say_row_op(RowOp(SCALE, 2, c=sp.Rational(1, 2))) == "multiply row three by one half"


@pytest.mark.parametrize("bad", [
    "Subtract 3 times row one.",           # digit
    "Now multiply by two.",                # number word
    "x squared is the answer",             # math word
    "so x = y",                            # math symbol
    "The answer is negative.",             # sign word
])
def test_lint_rejects_math_outside_placeholders(bad):
    assert lint_template(bad)


@pytest.mark.parametrize("good", [
    "Next, {op}, which puts a zero below the pivot in column {col}.",
    "Now the pivot is a leading one.",
    "Check the answer in the write-up.",
    "The tangent line touches the curve.",
])
def test_lint_accepts_prose(good):
    assert not lint_template(good)


def test_placeholders_must_be_filled_with_verified_values():
    assert Line("We {op}.", {}).problems()                      # missing value
    assert Line("We {op}.", {"op": "subtract"}).problems()      # not a Spoken
    assert not Line("We {op}.", {"op": OP(RowOp(SCALE, 0, c=sp.Integer(2)))}).problems()


@pytest.mark.parametrize("path", BENCH, ids=[p.stem for p in BENCH])
def test_every_benchmark_narration_is_clean(path):
    sol = solve_problem(load_problem(path)).solution
    builders = [generic.build]
    if sol.problem.type == "rref":
        builders.append(row_reduction.build)
    for build in builders:
        script = build(sol)
        lines = [v for v in script.values() if isinstance(v, Line)] + [ln for _, ln in script["steps"]]
        problems = [p for ln in lines for p in ln.problems()]
        assert not problems, problems


def test_caption_chunks_cover_the_spoken_text():
    line = Line("Next, {op}, which puts a zero below the pivot in column {col}. That completes the forward phase.",
                {"op": OP(RowOp(REPLACE, 1, 0, sp.Integer(-2))), "col": N(1)})
    chunks = caption_chunks(line, max_chars=40)
    assert len(chunks) >= 2
    spoken = " ".join(c[0] for c in chunks if c[0])
    assert " ".join(spoken.split()) == " ".join(line.spoken().split())
    assert all(len(c[1]) <= 70 for c in chunks)
