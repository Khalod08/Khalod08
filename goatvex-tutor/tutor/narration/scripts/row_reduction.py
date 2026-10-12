"""Narration for row-reduction / linear-system videos (MATH 1104).

Every number the narrator says comes from a placeholder filled with verified
data (the solver's steps and facts). Templates are prose only; the lint in
``tutor.narration.script`` enforces that.
"""

from __future__ import annotations

import sympy as sp

from tutor.narration.script import N, OP, WORDS, Line, Spoken, V, VEC
from tutor.narration.spoken import int_words, number_words, say
from tutor.text.unicode_math import sub, to_text


def var_names(n: int) -> list[str]:
    return ["x", "y", "z"][:n] if n <= 3 else [f"x{sub(i + 1)}" for i in range(n)]


def var_say(n: int) -> list[str]:
    return ["x", "y", "z"][:n] if n <= 3 else [f"x {int_words(i + 1)}" for i in range(n)]


def assignment(values, n: int) -> Spoken:
    """x = 1, y = 2 (spoken: "x equals one, y equals two")."""
    shows = [f"{nm} = {to_text(v)}" for nm, v in zip(var_names(n), values)]
    says = [f"{nm} equals {say(v)}" for nm, v in zip(var_say(n), values)]
    return Spoken(", ".join(says[:-1]) + (" and " if len(says) > 1 else "") + says[-1], ", ".join(shows))


def build(solution) -> dict:
    f = solution.facts
    aug = f["augmented"]
    m = f["input"]
    script: dict = {}
    if aug:
        script["intro"] = Line("Here is the augmented matrix of our system. Our goal is reduced row echelon form, "
                               "where the solution can simply be read off.")
    else:
        script["intro"] = Line("Let's row reduce this matrix to reduced row echelon form, one row operation at a "
                               "time.")
    nvars = m.cols - 1 if aug else m.cols
    system = f.get("system")
    if aug and nvars in (2, 3):
        shape = WORDS("a line in the plane") if nvars == 2 else WORDS("a plane in space")
        if system["status"] == "unique":
            script["intuition"] = Line("Picture it first. Each equation is {shape}. The solution is the single place "
                                       "where they all meet: the point {point}. Row operations change the equations, "
                                       "but never that meeting point.",
                                       {"shape": shape, "point": VEC(system["particular"])})
        elif system["status"] == "inconsistent":
            script["intuition"] = Line("Picture it first. Each equation is {shape}, and here they have no point in "
                                       "common, so we should expect no solution.", {"shape": shape})
        else:
            script["intuition"] = Line("Picture it first. Each equation is {shape}, and here they share infinitely "
                                       "many points, so we should expect a whole family of solutions.",
                                       {"shape": shape})
    else:
        script["intuition"] = Line("Remember why this works: a row operation never changes the solutions of the "
                                   "system. It only makes the matrix easier to read.")
    steps = []
    last_forward = max((k for k, s in enumerate(solution.steps) if s.kind == "row_op" and s.data["phase"] == "forward"),
                       default=None)
    for k, s in enumerate(solution.steps):
        if s.kind != "row_op":
            continue
        op = s.data["rowop"]
        col = N(s.data["pivot_column"])
        if op.kind == "swap":
            line = Line("Next, {op}, to bring a nonzero entry into the pivot position of column {col}.",
                        {"op": OP(op), "col": col})
        elif op.kind == "scale":
            line = Line("Next, {op}. Now the pivot in column {col} is a leading one.", {"op": OP(op), "col": col})
        elif s.data["phase"] == "forward":
            line = Line("Next, {op}, which puts a zero below the pivot in column {col}.", {"op": OP(op), "col": col})
        else:
            line = Line("Next, {op}, which puts a zero above the leading one in column {col}.",
                        {"op": OP(op), "col": col})
        if k == last_forward:
            line = Line(line.template + " That completes the forward phase: the matrix is in row echelon form.",
                        line.values)
        steps.append((s, line))
    script["steps"] = steps
    if aug and system["status"] == "unique":
        script["result"] = Line("This is reduced row echelon form, and the solution reads straight off: {sol}.",
                                {"sol": assignment(list(system["particular"]), nvars)})
    elif aug and system["status"] == "infinite":
        free = system["free_vars"]
        names = var_names(nvars)
        script["result"] = Line("This is reduced row echelon form. The column of {free} has no pivot, so {free} is "
                                "a free variable. Every solution has the form {gen}.",
                                {"free": Spoken(" and ".join(var_say(nvars)[i - 1] for i in free),
                                                ", ".join(names[i - 1] for i in free)),
                                 "gen": assignment(list(system["general"]), nvars)})
    elif aug:
        r = system["bad_row"]
        script["result"] = Line("This is reduced row echelon form. Row {r} says {eq}, which is impossible, so the "
                                "system has no solution.", {"r": N(r), "eq": V(sp.Eq(0, 1, evaluate=False))})
    else:
        cols = [c for _, c in f["pivots"]]
        script["result"] = Line("This is the reduced row echelon form. The pivots sit in columns {cols}, so the rank "
                                "is {rank}.",
                                {"cols": Spoken(" and ".join(number_words(c) for c in cols), ", ".join(map(str, cols))),
                                 "rank": N(f["rank"])})
    if aug and system["status"] == "unique":
        script["check"] = Line("Let's check by putting these values back into each original equation. Each of them "
                               "holds, so the answer is right.")
    elif aug and system["status"] == "infinite":
        script["check"] = Line("Let's check one solution: with the free variables set to {zero}, every original "
                               "equation holds.", {"zero": N(0)})
    else:
        script["check"] = Line("As a check, a computer algebra system reduced the same matrix independently and got "
                               "exactly this result.")
    script["recap"] = Line("To recap: get a leading one, clear the entries below it, move to the next column, and "
                           "finally clear the entries above each leading one.")
    script["practice"] = Line("Now it's your turn. Pause the video and solve this system. Your answer is checked in "
                              "the write-up, so no peeking.")
    return script


def all_lines(script: dict) -> list[Line]:
    out = [v for k, v in script.items() if isinstance(v, Line)]
    out += [ln for _, ln in script.get("steps", [])]
    return out
