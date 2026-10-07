"""Named sub-generators ("type:variant") for /practice and /testprep.

The course plans list the exact technique a week teaches, e.g.
"indefinite_integral:parts". Variants either have their own templates or
re-draw the type's generator until the requested task comes up. Every
generated problem still goes through the full solve + verify pipeline before
the student sees it (tutor/study/generate.py).
"""

from __future__ import annotations

import random

INTEGRAL_TECHNIQUES = {
    "basic": ["{a}x^{n} + {b}x - {c}", "{a}/x^2 + {b}sqrt(x)", "{a}e^x + {b}cos(x)", "{a}sec(x)^2 + {b}/x",
              "{a}sin(x) - {b}x^2"],
    "substitution": ["x({a}x^2 + {b})^{n}", "{a}x e^(x^2)", "sin(x) cos(x)^{n}", "{a}x/(x^2 + {b})",
                     "x^2 sqrt(x^3 + {b})", "ln(x)^{n}/x", "cos({a}x + {b})"],
    "parts": ["x e^({a}x)", "x cos({a}x)", "ln(x)", "x^2 e^x", "x sin({a}x)", "x ln(x)", "arctan(x)"],
    "partial_fractions": ["1/(x^2 - {b2})", "({a}x + {b})/(x^2 + 3x + 2)", "1/(x(x + {b}))",
                          "(x + {c})/((x - 1)(x + 2))"],
    "trig_powers": ["sin(x)^3", "sin(x)^2 cos(x)^3", "cos(x)^2", "sin(x)^2", "tan(x)^2 sec(x)^2", "tan(x)^3",
                    "sec(x)^4"],
    "trig_sub": ["1/sqrt(4 - x^2)", "sqrt(9 - x^2)", "1/(x^2 sqrt(x^2 + 4))", "1/sqrt(x^2 + 9)", "x^2/sqrt(1 - x^2)"],
}

LHOSPITAL = [("sin({b}x)/x", "0"), ("(e^x - 1)/x", "0"), ("(1 - cos(x))/x^2", "0"), ("ln(x)/(x - 1)", "1"),
             ("(e^({b}x) - 1)/sin(x)", "0"), ("x^2/e^x", "oo"), ("ln(x)/x", "oo"), ("(e^x - 1 - x)/x^2", "0")]


def _integral(technique: str):
    def gen(rng: random.Random, difficulty: int = 2):
        tpl = rng.choice(INTEGRAL_TECHNIQUES[technique])
        b = rng.randint(1, 5)
        f = tpl.format(a=rng.randint(2, 6), b=b, b2=b * b, c=rng.randint(1, 9), n=rng.randint(2, 4))
        return {"integrand": f, "variable": "x"}, f"Find ∫ {f} dx."
    return gen


def _lhospital(rng: random.Random, difficulty: int = 2):
    f, pt = rng.choice(LHOSPITAL)
    f = f.format(b=rng.randint(2, 5))
    return {"function": f, "variable": "x", "point": pt}, f"Find the limit of {f} as x → {pt}."


def _task(gen, task: str, key: str = "task"):
    """Re-draw ``gen`` until it produces the requested task (trying other difficulties if a task needs one)."""
    def g(rng: random.Random, difficulty: int = 2):
        for d in (difficulty, 1, 2, 3):
            for _ in range(60):
                given, statement = gen(rng, d)
                if given.get(key, "eigen" if key == "task" else None) == task:
                    return given, statement
        raise RuntimeError(f"generator never produced task {task!r}")
    return g


def attach(types: dict) -> None:
    ii = types["indefinite_integral"]
    for tech in INTEGRAL_TECHNIQUES:
        ii.variants[tech] = _integral(tech)
    types["limit"].variants["lhospital"] = _lhospital
    for name, tasks in (("subspaces", ("span", "independence", "bases")), ("eigen", ("eigen", "diagonalize")),
                        ("orthogonality", ("gram_schmidt", "projection")),
                        ("complex", ("simplify", "polar", "power", "roots", "quadratic"))):
        pt = types[name]
        for t in tasks:
            pt.variants[t] = _task(pt.generate, t)
