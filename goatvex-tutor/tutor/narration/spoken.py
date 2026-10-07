"""Turn verified SymPy objects into words for the voiceover.

Text-to-speech reads "1/3" as "one slash three" (or a date!) and "x^2" badly,
so every number and expression the narrator says is converted here, from the
verified object, never typed by hand:

    say(Rational(-3, 2))      → "negative three halves"
    say(3*x**2 + 1)           → "3 x squared plus 1"
    say_row_op(RowOp(...))    → "replace row 2 with row 2 minus 3 times row 1"
"""

from __future__ import annotations

import sympy as sp
from sympy.core.function import AppliedUndef

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
        "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
ORD = {2: "half", 3: "third", 4: "quarter", 5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth",
       10: "tenth", 11: "eleventh", 12: "twelfth", 16: "sixteenth", 20: "twentieth", 100: "hundredth"}
FUNC = {"sin": "sine", "cos": "cosine", "tan": "tangent", "sec": "secant", "csc": "cosecant", "cot": "cotangent",
        "asin": "arc sine", "acos": "arc cosine", "atan": "arc tangent", "log": "the natural log", "exp": "e to the"}


def int_words(n: int) -> str:
    if n < 0:
        return "negative " + int_words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else "-" + ONES[n % 10])
    if n < 1000:
        rest = n % 100
        return ONES[n // 100] + " hundred" + ("" if rest == 0 else " " + int_words(rest))
    if n < 1_000_000:
        rest = n % 1000
        return int_words(n // 1000) + " thousand" + ("" if rest == 0 else " " + int_words(rest))
    return str(n)  # big numbers: TTS reads digits fine


def number_words(q: sp.Expr) -> str:
    q = sp.nsimplify(q)
    if q.is_Integer:
        return int_words(int(q))
    if q.is_Rational:
        p, d = int(q.p), int(q.q)
        sign = "negative " if p < 0 else ""
        p = abs(p)
        if d in ORD:
            name = ORD[d]
            if p == 1:
                return f"{sign}one {name}"
            plural = "halves" if name == "half" else name + "s"
            return f"{sign}{int_words(p)} {plural}"
        return f"{sign}{int_words(p)} over {int_words(d)}"
    return say(q)


def say(e) -> str:
    """Spoken English for a SymPy expression (numbers in words)."""
    e = sp.sympify(e)
    return _say(e).replace("  ", " ").strip()


def _wrap(e) -> str:
    s = _say(e)
    return f"the quantity {s}," if (e.is_Add and len(e.args) > 1) else s


def _say(e) -> str:
    if isinstance(e, bool):
        return "true" if e else "false"
    if e.is_Number:
        if e is sp.oo:
            return "infinity"
        if e is sp.S.NegativeInfinity:
            return "negative infinity"
        return number_words(e)
    if e is sp.pi:
        return "pi"
    if e is sp.E:
        return "e"
    if e is sp.I:
        return "i"
    if e.is_Symbol:
        return str(e).replace("_", " ")
    if isinstance(e, AppliedUndef):
        return e.func.__name__
    if isinstance(e, sp.Derivative):
        v = _say(e.variables[0])
        if isinstance(e.expr, AppliedUndef):
            return f"d {e.expr.func.__name__} d {v}"
        return f"the derivative with respect to {v} of {_wrap(e.expr)}"
    if isinstance(e, sp.Integral):
        v = _say(e.variables[0])
        lim = e.limits[0]
        if len(lim) == 3:
            return f"the integral from {_say(lim[1])} to {_say(lim[2])} of {_wrap(e.function)} d {v}"
        return f"the integral of {_wrap(e.function)} d {v}"
    if isinstance(e, sp.Abs):
        return f"the absolute value of {_say(e.args[0])}"
    if e.is_Add:
        terms = list(e.as_ordered_terms()) if not _hand(e) else list(e.args)
        out = _say(terms[0])
        for t in terms[1:]:
            c, rest = t.as_coeff_Mul()
            if c.is_Number and c < 0:
                out += " minus " + _say(-t)
            else:
                out += " plus " + _say(t)
        return out
    if e.is_Mul:
        num, den = sp.fraction(e) if not _hand(e) else (e, sp.Integer(1))
        if den != 1:
            return f"{_wrap(num)} over {_wrap(den)}"
        c, rest = e.as_coeff_Mul() if not _hand(e) else (sp.Integer(1), e)
        parts = []
        if c == -1:
            parts.append("negative")
        elif c != 1:
            parts.append(number_words(c))
        factors = list(rest.args) if rest.is_Mul else [rest]
        for k, f in enumerate(factors):
            if _hand(e) and k > 0 and f.is_Number:
                parts.append("times")
            parts.append(_wrap(f))
        return " ".join(parts)
    if e.is_Pow:
        b, x = e.args
        if x == sp.Rational(1, 2):
            return f"the square root of {_wrap(b)}"
        if x == -1:
            return f"one over {_wrap(b)}"
        if x == 2:
            return f"{_wrap(b)} squared"
        if x == 3:
            return f"{_wrap(b)} cubed"
        if b is sp.E:
            return f"e to the {_wrap(x)}"
        return f"{_wrap(b)} to the power {_wrap(x)}"
    if isinstance(e, sp.exp):
        return f"e to the {_wrap(e.args[0])}"
    if isinstance(e, sp.Function):
        name = FUNC.get(e.func.__name__, e.func.__name__)
        return f"{name} of {_wrap(e.args[0])}"
    if isinstance(e, sp.Equality):
        return f"{_say(e.lhs)} equals {_say(e.rhs)}"
    return str(e)


def _hand(e) -> bool:
    try:
        return e.func(*e.args) != e or (e.is_Mul and sum(1 for a in e.args if a.is_Number) > 1)
    except Exception:
        return False


def say_row_op(op) -> str:
    """Spoken version of an elementary row operation."""
    i = int_words(op.i + 1)
    if op.kind == "swap":
        return f"swap row {i} and row {int_words(op.j + 1)}"
    if op.kind == "scale":
        return f"multiply row {i} by {number_words(op.c)}"
    j = int_words(op.j + 1)
    word = "minus" if op.c < 0 else "plus"
    mag = abs(op.c)
    times = "" if mag == 1 else f"{number_words(mag)} times "
    return f"replace row {i} with row {i} {word} {times}row {j}"


def say_vector(v) -> str:
    return ", ".join(_say(sp.sympify(c)) for c in v)
