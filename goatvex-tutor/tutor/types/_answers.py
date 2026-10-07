"""Parse what a student types as an answer, and compare it with a verified one.

Answers are typed in plain text, e.g.

    matrix:      1 0 2; 0 1 3          (rows separated by ';')
    vector:      (1, -2, 3)  or  1, -2, 3
    expression:  3x^2 + 2/x
    number:      -7/2
    complex:     3 - 4i
    list:        x = 1, 2, -3
"""

from __future__ import annotations

import re

import sympy as sp

from tutor.errors import ProblemFormatError
from tutor.parse.schema import parse_math
from tutor.text.unicode_math import to_text
from tutor.verify.equivalence import check_equal
from tutor.verify.result import PASS

_UNICODE = {"−": "-", "·": "*", "×": "*", "²": "^2", "³": "^3", "√": "sqrt", "π": "pi", "∞": "oo"}


def normalize(text: str) -> str:
    for a, b in _UNICODE.items():
        text = text.replace(a, b)
    return text.strip()


def parse_answer_expr(text: str, variables=(), imaginary=False) -> sp.Expr:
    text = normalize(text)
    text = re.sub(r"^[A-Za-z]\w*(\([A-Za-z]\))?\s*['′]*\s*=", "", text).strip()  # drop "f'(x) =" / "y ="
    text = re.sub(r"\+\s*C\s*$", "", text).strip()  # antiderivative constant
    return parse_math(text, list(variables), imaginary=imaginary)


def parse_answer_matrix(text: str) -> sp.Matrix:
    text = normalize(text).strip("[]() ")
    rows = [r for r in re.split(r";|\n|\]\s*,?\s*\[", text) if r.strip()]
    parsed = [[parse_math(c) for c in re.split(r"[,\s]+", r.strip(" []()")) if c] for r in rows]
    if not parsed or len({len(r) for r in parsed}) != 1:
        raise ProblemFormatError("rows must all have the same number of entries (separate rows with ';')")
    return sp.Matrix(parsed)


def parse_answer_list(text: str, imaginary=False) -> list[sp.Expr]:
    text = normalize(text)
    text = re.sub(r"^[^=]*=", "", text) if text.count("=") == 1 else text
    parts = [p for p in re.split(r"[,;]", text.strip(" ()[]{}")) if p.strip()]
    return [parse_math(p, imaginary=imaginary) for p in parts]


def same_expr(student: sp.Expr, verified: sp.Expr, symbols=None) -> tuple[bool, str]:
    status, detail = check_equal(student, verified, symbols)
    return status == PASS, detail


def grade_expr(verified: sp.Expr, text: str, variables=(), *, up_to_constant=False, imaginary=False) -> tuple[bool, str]:
    try:
        student = parse_answer_expr(text, variables, imaginary=imaginary)
    except ProblemFormatError as exc:
        return False, f"I couldn't read that answer ({exc})."
    syms = [sp.Symbol(v, real=True) for v in variables]
    if up_to_constant:
        x = syms[0]
        ok, _ = same_expr(sp.diff(student, x), sp.diff(verified, x), syms)
    else:
        ok, _ = same_expr(student, verified, syms or None)
    return ok, ("Correct!" if ok else f"Not quite. Your answer {to_text(student)} isn't equal to the verified answer.")


def grade_matrix(verified: sp.Matrix, text: str) -> tuple[bool, str]:
    try:
        student = parse_answer_matrix(text)
    except Exception as exc:
        return False, f"I couldn't read that matrix ({exc}). Type rows separated by ';', e.g. 1 0; 0 1"
    if student.shape != verified.shape:
        return False, f"Your matrix is {student.rows}×{student.cols}, but the answer is {verified.rows}×{verified.cols}."
    wrong = [(i + 1, j + 1) for i in range(student.rows) for j in range(student.cols)
             if sp.simplify(student[i, j] - verified[i, j]) != 0]
    if not wrong:
        return True, "Correct!"
    where = ", ".join(f"({i},{j})" for i, j in wrong[:4])
    return False, f"Not quite: entry {where} {'is' if len(wrong) == 1 else 'are'} off."


def grade_list(verified: list, text: str, *, ordered=True, imaginary=False) -> tuple[bool, str]:
    try:
        student = parse_answer_list(text, imaginary=imaginary)
    except Exception as exc:
        return False, f"I couldn't read that ({exc})."
    if len(student) != len(verified):
        return False, f"I expected {len(verified)} value(s) but read {len(student)}."
    if ordered:
        ok = all(sp.simplify(a - b) == 0 for a, b in zip(student, verified))
    else:
        remaining = list(verified)
        ok = True
        for a in student:
            match = next((b for b in remaining if sp.simplify(a - b) == 0), None)
            if match is None:
                ok = False
                break
            remaining.remove(match)
    return ok, "Correct!" if ok else "Not quite. At least one value is off."


def parse_answer_vectors(text: str) -> list[sp.Matrix]:
    """'(1, 2, 3), (0, -1, 1)' → two column vectors."""
    groups = re.findall(r"[(\[]([^()\[\]]*)[)\]]", normalize(text))
    if not groups:
        raise ProblemFormatError("write each vector in brackets, e.g. (1, 2, 3), (0, -1, 1)")
    return [sp.Matrix([parse_math(c) for c in re.split(r"[,\s]+", g.strip()) if c]) for g in groups]


def vectors_text(vs) -> str:
    return ", ".join("(" + ", ".join(str(e) for e in v) + ")" for v in vs)


def grade_orthogonal_basis(original: list[sp.Matrix], text: str) -> tuple[bool, str]:
    """Any orthogonal basis of span(original) is right (Gram–Schmidt answers differ by scaling and order)."""
    try:
        vs = parse_answer_vectors(text)
    except Exception as exc:  # noqa: BLE001
        return False, f"I couldn't read that ({exc})."
    W = sp.Matrix.hstack(*original)
    dim = W.rank()
    if any(v.rows != W.rows for v in vs):
        return False, f"Each vector should have {W.rows} entries."
    if len(vs) != dim:
        return False, f"A basis of W has {dim} vectors; you gave {len(vs)}."
    if any(v.is_zero_matrix for v in vs):
        return False, "A basis can't contain the zero vector."
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            if sp.simplify(vs[i].dot(vs[j])) != 0:
                return False, f"Vectors {i + 1} and {j + 1} are not orthogonal (their dot product isn't 0)."
    if sp.Matrix.hstack(W, *vs).rank() != dim:
        return False, "At least one of your vectors is not in W."
    return True, "Correct! (Any nonzero multiples of these vectors are also right.)"
