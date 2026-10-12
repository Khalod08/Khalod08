"""Multiple-choice options for MATH 1004's multiple-choice final.

The right option is the verified answer. Each distractor is a typical mistake
(sign error, factor of two, off by one, missing reciprocal …) and is only
used if the equivalence checker PROVES it differs from the verified answer
(status FAIL), so a "wrong" option can never secretly be right.
"""

from __future__ import annotations

import random

import sympy as sp

from tutor.text.latex import latex_of
from tutor.text.unicode_math import to_text
from tutor.verify.equivalence import check_equal
from tutor.verify.result import FAIL

LETTERS = "ABCDE"


def _candidates(a: sp.Expr) -> list[sp.Expr]:
    out = [-a, 2 * a, a / 2]
    if a.is_number:
        out += [a + 1, a - 1, 1 / a if a != 0 else sp.Integer(1), a ** 2]
    else:
        out += [a + 1, sp.expand(a * 3) / 2]
    return out


def choices(sol, rng: random.Random, n: int = 4) -> dict | None:
    ans = sol.answer
    if isinstance(ans, sp.Equality):
        ans = ans.rhs
    if not isinstance(ans, sp.Expr) or ans.has(sp.oo, -sp.oo, sp.zoo, sp.nan):
        return None
    if isinstance(ans, sp.Symbol) and ("_" in ans.name or ans.name == "DNE"):  # "not_invertible", "DNE" …
        return None
    syms = sorted(ans.free_symbols, key=str)
    if sol.problem.type == "indefinite_integral":
        # antiderivatives are equal up to a constant: compare derivatives, so F + 1 is never a "wrong" option
        x = sol.facts.get("variable", syms[0] if syms else sp.Symbol("x"))
        key = lambda e: sp.diff(e, x)  # noqa: E731
    else:
        key = lambda e: e  # noqa: E731
    picked: list[sp.Expr] = []
    for c in _candidates(ans):
        try:
            c = sp.simplify(c)
            if check_equal(key(c), key(ans), syms)[0] != FAIL:
                continue
            if any(check_equal(key(c), key(q), syms)[0] != FAIL for q in picked):
                continue
        except Exception:  # noqa: BLE001
            continue
        picked.append(c)
        if len(picked) == n - 1:
            break
    if len(picked) < n - 1:
        return None
    opts = picked + [ans]
    rng.shuffle(opts)
    k = opts.index(ans)
    return {"choices": [{"letter": LETTERS[i], "text": to_text(o), "latex": latex_of(o)} for i, o in enumerate(opts)],
            "correct_choice": LETTERS[k]}
