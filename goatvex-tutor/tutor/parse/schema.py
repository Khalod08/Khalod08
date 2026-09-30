"""problem.json: the structured, SymPy-parseable form of a problem.

Every problem GoatVex solves is first transcribed into this format, shown to the
student in readable form, and only solved after the student confirms it
(``confirmed_by_student: true``).

Example (see ``tutor/parse/problem.schema.json`` for the full JSON Schema)::

    {
      "schema_version": 1,
      "slug": "rref-3x4-textbook-1-2-7",
      "course": "MATH1104",
      "topic": "row-reduction",
      "type": "rref",
      "statement": "Row reduce the augmented matrix of the system ...",
      "given": {"matrix": [["1", "2", "-1", "3"], ...], "augmented": true},
      "source": {"kind": "typed", "ref": ""},
      "context": {"graded": false},
      "confirmed_by_student": false
    }

Matrix entries and functions are *strings* so that fractions stay exact
("1/3" is parsed as the rational 1/3, never the float 0.333...).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from tutor.errors import ProblemFormatError

SCHEMA_VERSION = 1
COURSES = ("MATH1104", "MATH1004")

# type -> (default topic, required keys in "given")
PROBLEM_TYPES: dict[str, tuple[str, tuple[str, ...]]] = {
    "rref": ("row-reduction", ("matrix",)),
    "matrix_inverse": ("matrix-inverse", ("matrix",)),
    "derivative": ("derivatives", ("function", "variable")),
}

_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _local_dict(variables: list[str] | None = None) -> dict[str, Any]:
    names: dict[str, Any] = {
        "e": sp.E,
        "E": sp.E,
        "pi": sp.pi,
        "ln": sp.log,
        "log": sp.log,
        "sqrt": sp.sqrt,
        "arcsin": sp.asin,
        "arccos": sp.acos,
        "arctan": sp.atan,
    }
    for v in variables or []:
        names[v] = sp.Symbol(v, real=True)
    return names


def parse_math(text: str | int, variables: list[str] | None = None) -> sp.Expr:
    """Parse a math string exactly (no floats) into a SymPy expression.

    Accepts ``^`` for powers, implicit multiplication (``3x``), ``ln``, ``e``.
    Decimal inputs such as ``0.5`` are converted to exact rationals.
    """
    if isinstance(text, bool):
        raise ProblemFormatError(f"expected a math expression, got {text!r}")
    if isinstance(text, int):
        return sp.Integer(text)
    if not isinstance(text, str) or not text.strip():
        raise ProblemFormatError(f"expected a non-empty math string, got {text!r}")
    try:
        expr = parse_expr(
            text.strip(),
            local_dict=_local_dict(variables),
            transformations=_TRANSFORMS,
            evaluate=True,
        )
    except Exception as exc:  # SymPy raises many different types here
        raise ProblemFormatError(f"could not parse {text!r}: {exc}") from exc
    expr = sp.nsimplify(expr, rational=True) if expr.has(sp.Float) else expr
    return sp.sympify(expr)


def parse_matrix(rows: Any) -> sp.Matrix:
    if not isinstance(rows, list) or not rows or not all(isinstance(r, list) and r for r in rows):
        raise ProblemFormatError("matrix must be a non-empty list of non-empty rows")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ProblemFormatError("all matrix rows must have the same length")
    return sp.Matrix([[parse_math(v) for v in r] for r in rows])


@dataclass
class Problem:
    slug: str
    course: str
    topic: str
    type: str
    statement: str
    given: dict[str, Any]
    source: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    confirmed_by_student: bool = False
    expected: dict[str, Any] | None = None  # benchmark problems only
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # ---- parsed views of "given" -------------------------------------------------
    @property
    def matrix(self) -> sp.Matrix:
        return parse_matrix(self.given["matrix"])

    @property
    def variable(self) -> sp.Symbol:
        return sp.Symbol(self.given["variable"], real=True)

    @property
    def function(self) -> sp.Expr:
        return parse_math(self.given["function"], [self.given["variable"]])

    @property
    def is_graded(self) -> bool:
        return bool(self.context.get("graded", False))

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out.update(
            schema_version=SCHEMA_VERSION,
            slug=self.slug,
            course=self.course,
            topic=self.topic,
            type=self.type,
            statement=self.statement,
            given=self.given,
            source=self.source,
            context=self.context,
            confirmed_by_student=self.confirmed_by_student,
        )
        if self.expected is not None:
            out["expected"] = self.expected
        return out


def problem_from_dict(data: dict[str, Any]) -> Problem:
    """Validate a problem dict and return a :class:`Problem`.

    Raises :class:`ProblemFormatError` with a readable message on any problem.
    """
    if not isinstance(data, dict):
        raise ProblemFormatError("problem.json must contain a JSON object")
    version = data.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise ProblemFormatError(f"unsupported schema_version {version}")

    ptype = data.get("type")
    if ptype not in PROBLEM_TYPES:
        raise ProblemFormatError(
            f"unknown problem type {ptype!r}; supported: {', '.join(sorted(PROBLEM_TYPES))}"
        )
    default_topic, required = PROBLEM_TYPES[ptype]

    course = data.get("course")
    if course not in COURSES:
        raise ProblemFormatError(f"course must be one of {COURSES}, got {course!r}")

    slug = data.get("slug", "")
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise ProblemFormatError(
            f"slug must be lowercase words joined by dashes (e.g. 'rref-3x3-q4'), got {slug!r}"
        )

    given = data.get("given")
    if not isinstance(given, dict):
        raise ProblemFormatError("'given' must be an object")
    missing = [k for k in required if k not in given]
    if missing:
        raise ProblemFormatError(f"'given' is missing {missing} for type {ptype!r}")

    problem = Problem(
        slug=slug,
        course=course,
        topic=data.get("topic") or default_topic,
        type=ptype,
        statement=str(data.get("statement", "")),
        given=given,
        source=data.get("source") or {},
        context=data.get("context") or {},
        confirmed_by_student=bool(data.get("confirmed_by_student", False)),
        expected=data.get("expected"),
        raw=data,
    )

    # Parse eagerly so format errors surface before the student confirms.
    if ptype in ("rref", "matrix_inverse"):
        m = problem.matrix
        if ptype == "matrix_inverse" and not m.is_square:
            raise ProblemFormatError("matrix_inverse needs a square matrix")
        if given.get("augmented") and m.cols < 2:
            raise ProblemFormatError("an augmented matrix needs at least 2 columns")
    elif ptype == "derivative":
        var = given["variable"]
        if not isinstance(var, str) or not re.fullmatch(r"[A-Za-z]", var):
            raise ProblemFormatError("'variable' must be a single letter such as 'x'")
        f = problem.function
        extra = f.free_symbols - {problem.variable}
        if extra:
            raise ProblemFormatError(
                f"function has symbols other than {var}: {sorted(map(str, extra))}"
            )
    return problem


def load_problem(path: str | Path) -> Problem:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProblemFormatError(f"{path} is not valid JSON: {exc}") from exc
    return problem_from_dict(data)


def save_problem(problem: Problem, path: str | Path) -> None:
    Path(path).write_text(json.dumps(problem.to_json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
