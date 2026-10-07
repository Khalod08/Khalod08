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

_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _local_dict(variables: list[str] | None = None, imaginary: bool = False) -> dict[str, Any]:
    names: dict[str, Any] = {
        "oo": sp.oo,
        "inf": sp.oo,
        "infinity": sp.oo,
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
    if imaginary:
        names["i"] = sp.I
        names["I"] = sp.I
    for v in variables or []:
        names[v] = sp.Symbol(v, real=True)
    return names


def parse_math(text: str | int, variables: list[str] | None = None, imaginary: bool = False,
               evaluate: bool = True) -> sp.Expr:
    """Parse a math string exactly (no floats) into a SymPy expression.

    Accepts ``^`` for powers, implicit multiplication (``3x``), ``ln``, ``e``.
    Decimal inputs such as ``0.5`` are converted to exact rationals.
    """
    if isinstance(text, bool):
        raise ProblemFormatError(f"expected a math expression, got {text!r}")
    if isinstance(text, int):
        return sp.Integer(text)
    if isinstance(text, float):
        return sp.nsimplify(text, rational=True)
    if not isinstance(text, str) or not text.strip():
        raise ProblemFormatError(f"expected a non-empty math string, got {text!r}")
    try:
        expr = parse_expr(
            text.strip(),
            local_dict=_local_dict(variables, imaginary),
            transformations=_TRANSFORMS,
            evaluate=evaluate,
        )
    except Exception as exc:  # SymPy raises many different types here
        raise ProblemFormatError(f"could not parse {text!r}: {exc}") from exc
    if expr.has(sp.Float):
        expr = expr.xreplace({f: sp.nsimplify(f, rational=True) for f in expr.atoms(sp.Float)})
    return expr if not evaluate else sp.sympify(expr)


def parse_matrix(rows: Any) -> sp.Matrix:
    if not isinstance(rows, list) or not rows or not all(isinstance(r, list) and r for r in rows):
        raise ProblemFormatError("matrix must be a non-empty list of non-empty rows")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ProblemFormatError("all matrix rows must have the same length")
    return sp.Matrix([[parse_math(v) for v in r] for r in rows])


def parse_vector(entries: Any) -> sp.Matrix:
    if not isinstance(entries, list) or not entries or any(isinstance(e, list) for e in entries):
        raise ProblemFormatError(f"a vector must be a flat list of numbers, got {entries!r}")
    return sp.Matrix([parse_math(e) for e in entries])


def require_variable(problem: "Problem") -> sp.Symbol:
    var = problem.given.get("variable")
    if not isinstance(var, str) or not re.fullmatch(r"[A-Za-z]", var):
        raise ProblemFormatError("'variable' must be a single letter such as 'x'")
    return sp.Symbol(var, real=True)


def require_only(expr: sp.Expr, allowed: set, what: str) -> None:
    extra = expr.free_symbols - set(allowed)
    if extra:
        names = ", ".join(sorted(map(str, extra)))
        raise ProblemFormatError(f"{what} contains unexpected symbol(s) {names}")


def require_numeric_matrix(m: sp.Matrix, what: str = "matrix") -> None:
    for e in m:
        if e.free_symbols:
            raise ProblemFormatError(f"{what} entries must be numbers (found {e})")


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
    def variables(self) -> list[str]:
        if "variables" in self.given:
            return list(self.given["variables"])
        if "variable" in self.given:
            return [self.given["variable"]]
        return []

    @property
    def variable(self) -> sp.Symbol:
        return sp.Symbol(self.given["variable"], real=True)

    @property
    def matrix(self) -> sp.Matrix:
        return parse_matrix(self.given["matrix"])

    @property
    def function(self) -> sp.Expr:
        return self.expr("function")

    def expr(self, key: str, *, imaginary: bool = False, extra_vars: list[str] | None = None) -> sp.Expr:
        return parse_math(self.given[key], self.variables + (extra_vars or []), imaginary=imaginary)

    def mat(self, key: str) -> sp.Matrix:
        return parse_matrix(self.given[key])

    def vec(self, key: str) -> sp.Matrix:
        """A vector written as a list ["1", "2", "3"] → column matrix."""
        return parse_vector(self.given[key])

    def vecs(self, key: str) -> list[sp.Matrix]:
        vs = self.given[key]
        if not isinstance(vs, list) or not vs:
            raise ProblemFormatError(f"'{key}' must be a non-empty list of vectors")
        out = [parse_vector(v) for v in vs]
        if len({v.rows for v in out}) != 1:
            raise ProblemFormatError(f"all vectors in '{key}' must have the same number of entries")
        return out

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

    from tutor import registry

    types = registry.load_all()
    ptype = data.get("type")
    if ptype not in types:
        raise ProblemFormatError(
            f"unknown problem type {ptype!r}; supported: {', '.join(sorted(types))}"
        )
    pt = types[ptype]

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
    missing = [k for k in pt.required if k not in given]
    if missing:
        raise ProblemFormatError(f"'given' is missing {missing} for type {ptype!r}")

    problem = Problem(
        slug=slug,
        course=course,
        topic=data.get("topic") or pt.topic,
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
    try:
        pt.validate(problem)
    except ProblemFormatError:
        raise
    except Exception as exc:  # a parse error deep inside SymPy, a bad key, ...
        raise ProblemFormatError(f"could not read the problem: {type(exc).__name__}: {exc}") from exc
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
