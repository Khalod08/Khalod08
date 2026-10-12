"""Complex numbers (Nicholson Appendix A): arithmetic, polar form, De Moivre, roots.

Tasks (``given.task``):

* ``simplify``  write an expression like (2 + 3i)(1 − i)/(1 + 2i) as a + bi
* ``polar``     modulus r, principal argument θ ∈ (−π, π], and polar form r(cos θ + i sin θ)
* ``power``     zⁿ by De Moivre's theorem
* ``roots``     the n nth roots of w
* ``quadratic`` solve az² + bz + c = 0 (real coefficients, any discriminant)

Every multiplication is shown FOIL-style, i² = −1 gets its own step, and
division multiplies top and bottom by the conjugate of the bottom.
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem, parse_math
from tutor.solvers.builder import Builder
from tutor.steps import FACT, SETUP, Solution, Step
from tutor.text.unicode_math import sub, to_text

I = sp.I


def _m(*a):
    return sp.Mul(*a, evaluate=False)


def _a(*a):
    return sp.Add(*a, evaluate=False)


def parts(z) -> tuple[sp.Expr, sp.Expr]:
    z = sp.expand_complex(sp.sympify(z))
    return sp.re(z), sp.im(z)


def canon(z) -> sp.Expr:
    """a + bi with exact a, b."""
    a, b = parts(z)
    return sp.simplify(a) + sp.simplify(b) * I


def _binomial(a, b):
    """a + bi as an unevaluated sum (zero parts dropped)."""
    if b == 0:
        return a
    bi = I if b == 1 else (-I if b == -1 else _m(b, I))
    return bi if a == 0 else _a(a, bi)


def multiply(B: Builder, z1, z2) -> sp.Expr:
    a, b = parts(z1)
    c, d = parts(z2)
    if b == 0 or d == 0:  # a real times a complex number: just distribute
        result = canon(z1 * z2)
        B.add(_m(_binomial(a, b), _binomial(c, d)), "Multiply", result,
              "Multiply the real number into both parts.")
        return result
    foil = _a(_m(a, c), _m(a, d, I), _m(b, c, I), _m(b, d, sp.Pow(I, 2, evaluate=False)))
    B.add(_m(_binomial(a, b), _binomial(c, d)), "Expand (FOIL)", foil,
          "Multiply every term of the first factor by every term of the second.")
    use_i2 = _a(_m(a, c), _m(a, d, I), _m(b, c, I), _m(b, d, -1))
    B.add(foil, "Use i² = −1", use_i2, "Replace i² by −1.")
    result = canon(z1 * z2)
    B.add(use_i2, "Combine", result, "Collect the real parts and the imaginary parts.")
    return result


def divide(B: Builder, z1, z2) -> sp.Expr:
    c, d = parts(z2)
    if d == 0:
        result = canon(z1 / c)
        B.add(_m(z1, sp.Pow(c, -1, evaluate=False)), "Divide", result, "Divide both parts by the real number.")
        return result
    conj = _binomial(c, -d)
    top = _m(_binomial(*parts(z1)), conj)
    bottom = _m(_binomial(c, d), conj)
    B.add(_m(_binomial(*parts(z1)), sp.Pow(_binomial(c, d), -1, evaluate=False)),
          "Multiply by the conjugate", _m(top, sp.Pow(bottom, -1, evaluate=False)),
          f"Multiply top and bottom by the conjugate of the bottom, {to_text(conj)}.")
    num = multiply(B, z1, c - d * I)
    den_sum = _a(sp.Pow(c, 2, evaluate=False), sp.Pow(d, 2, evaluate=False))
    den = c**2 + d**2
    B.add(bottom, "Bottom: (c + di)(c − di) = c² + d²", den_sum, "A number times its conjugate is real: c² + d².")
    B.add(den_sum, "Arithmetic", den, "Add.")
    result = canon(num / den)
    B.add(_m(num, sp.Pow(den, -1, evaluate=False)), "Divide", result, "Divide the real and imaginary parts by the bottom.")
    return result


def _is_leaf(t) -> bool:
    return t.is_Number or t == I or (t.is_Mul and len(t.args) == 2 and t.args[0].is_Number and t.args[1] == I) \
        or (t.is_Pow and t.exp == sp.Rational(1, 2) and t.base.is_Number) \
        or (t.is_Mul and all(a.is_Number or a == I or (a.is_Pow and a.base.is_Number) for a in t.args))


def _is_binomial(node) -> bool:
    """a + bi with at most one real term and one imaginary term."""
    if not all(_is_leaf(t) for t in node.args) or len(node.args) > 2:
        return False
    real = [t for t in node.args if not t.has(I)]
    imag = [t for t in node.args if t.has(I)]
    return len(real) <= 1 and len(imag) <= 1


def evaluate(B: Builder, node) -> sp.Expr:
    if _is_leaf(node) and not node.is_Add:
        return canon(node)
    if node.is_Number or node == I or node.is_Symbol:
        return node
    if node.is_Mul and len(node.args) == 2 and node.args[0].is_Number and node.args[1] == I:
        return node
    if isinstance(node, sp.conjugate):
        z = evaluate(B, node.args[0])
        a, b = parts(z)
        return B.add(sp.conjugate(_binomial(a, b), evaluate=False), "Conjugate", canon(a - b * I),
                     "The conjugate flips the sign of the imaginary part.")
    if isinstance(node, sp.Abs):
        z = evaluate(B, node.args[0])
        a, b = parts(z)
        formula = sp.sqrt(_a(sp.Pow(a, 2, evaluate=False), sp.Pow(b, 2, evaluate=False)), evaluate=False)
        B.add(sp.Abs(_binomial(a, b), evaluate=False), "Modulus", formula, "|a + bi| = √(a² + b²).")
        return B.add(formula, "Arithmetic", sp.sqrt(a**2 + b**2), "Simplify.")
    if node.is_Add and _is_binomial(node):
        return canon(node)  # already a + bi: nothing to do
    if node.is_Add:
        vals = [evaluate(B, t) for t in node.args]
        result = canon(sum(vals))
        if len(vals) > 1:
            B.add(_a(*[_binomial(*parts(v)) for v in vals]), "Add", result,
                  "Add the real parts and add the imaginary parts.")
        return result
    if node.is_Pow:
        base, n = node.args
        if not n.is_Integer:
            raise UnsupportedProblem("only whole-number powers are supported here (use the 'roots' task for nth roots)")
        z = evaluate(B, base)
        n = int(n)
        if n < 0:
            inv = divide(B, sp.Integer(1), z)
            z, n = inv, -n
            if n == 1:
                return inv
        if z == I or z == -I:
            r = n % 4
            result = (z ** r) if r else sp.Integer(1)
            result = canon(result)
            B.add(sp.Pow(z, n, evaluate=False), "Powers of i", result,
                  f"Powers of i repeat every 4: i⁴ = 1, so i^{n} = i^{r}." if z == I else
                  f"(−i)^{n}: powers repeat every 4.")
            return result
        if n > 4:
            raise UnsupportedProblem(f"for a power as high as {n}, use the 'power' task (De Moivre's theorem)")
        result = z
        for _ in range(n - 1):
            result = multiply(B, result, z)
        return result
    if node.is_Mul:
        factors = list(node.args)
        num = [f for f in factors if not (f.is_Pow and f.exp.is_Integer and f.exp < 0)]
        den = [f.base ** (-f.exp) for f in factors if f.is_Pow and f.exp.is_Integer and f.exp < 0]
        vals = [evaluate(B, f) for f in num]
        acc = vals[0] if vals else sp.Integer(1)
        for v in vals[1:]:
            acc = multiply(B, acc, v)
        for dnode in den:
            dv = evaluate(B, dnode)
            acc = divide(B, acc, dv)
        return acc
    raise UnsupportedProblem(f"I can't handle {to_text(node)} step by step yet")


def principal_arg(a, b) -> sp.Expr:
    if a == 0 and b == 0:
        raise UnsupportedProblem("0 has no argument")
    return sp.atan2(b, a)


QUADRANT = {(1, 1): "I", (-1, 1): "II", (-1, -1): "III", (1, -1): "IV"}


def polar_steps(B: Builder, z) -> tuple[sp.Expr, sp.Expr]:
    a, b = parts(z)
    formula = sp.sqrt(_a(sp.Pow(a, 2, evaluate=False), sp.Pow(b, 2, evaluate=False)), evaluate=False)
    r = sp.sqrt(a**2 + b**2)
    B.add(formula, "Modulus r = √(a² + b²)", r, f"Here a = {to_text(a)} and b = {to_text(b)}.")
    theta = sp.simplify(principal_arg(a, b))
    if a != 0 and b != 0:
        q = QUADRANT[(int(sp.sign(a)), int(sp.sign(b)))]
        ref = sp.atan(sp.Abs(b) / sp.Abs(a))
        why = (f"tan α = |b|/|a| = {to_text(sp.Abs(b) / sp.Abs(a))} gives the reference angle α = {to_text(ref)}. "
               f"The point ({to_text(a)}, {to_text(b)}) is in quadrant {q}, so θ = {to_text(theta)} (−π < θ ≤ π).")
    else:
        why = f"The point ({to_text(a)}, {to_text(b)}) lies on an axis, so θ = {to_text(theta)}."
    B.add(theta, "Argument θ", theta, why, kind=FACT, fact="argument")
    return r, theta


def polar_form(r, theta):
    return _m(r, _a(sp.cos(theta, evaluate=False), _m(I, sp.sin(theta, evaluate=False))))


def solve(p: Problem) -> Solution:
    task = p.given["task"]
    B = Builder()
    facts: dict = {"task": task}
    notes: list[str] = []
    if task == "simplify":
        expr = parse_math(p.given["expression"], imaginary=True, evaluate=False)
        B.steps.append(Step(id="s0", kind=SETUP, before=expr, operation="Write the expression", after=expr,
                            justification="Work from the inside out, one operation at a time.", data={"chain": False}))
        answer = evaluate(B, expr)
        facts["expression"] = expr
        label = "a + bi"
    elif task == "polar":
        z = canon(parse_math(p.given["z"], imaginary=True))
        r, theta = polar_steps(B, z)
        form = polar_form(r, theta)
        B.add(form, "Polar form", form, "z = r(cos θ + i sin θ). Exponential form: z = r·e^(iθ).", kind=FACT,
              fact="polar_form")
        facts.update(z=z, r=r, theta=theta)
        answer, label = form, "z = r(cos θ + i sin θ)"
        notes.append(f"r = {to_text(r)}, θ = {to_text(theta)}; exponential form z = {to_text(r)}e^(i{to_text(theta)}).")
    elif task == "power":
        z = canon(parse_math(p.given["z"], imaginary=True))
        n = int(p.given["n"])
        r, theta = polar_steps(B, z)
        dm = _m(sp.Pow(r, n, evaluate=False), _a(sp.cos(_m(n, theta)), _m(I, sp.sin(_m(n, theta)))))
        B.add(sp.Pow(polar_form(r, theta), n, evaluate=False), "De Moivre's theorem", dm,
              f"[r(cos θ + i sin θ)]ⁿ = rⁿ(cos nθ + i sin nθ) with n = {n}.")
        nt = n * theta
        reduced = _reduce_angle(nt)
        simple = _m(r**n, _a(sp.cos(reduced, evaluate=False), _m(I, sp.sin(reduced, evaluate=False))))
        why = f"{n}·θ = {to_text(nt)}" + (f", which is the same angle as {to_text(reduced)} (subtract multiples of 2π)."
                                         if reduced != nt else ".")
        B.add(dm, "Simplify the angle", simple, why)
        answer = canon(r**n * (sp.cos(reduced) + I * sp.sin(reduced)))
        B.add(simple, "Evaluate cos and sin", answer, "Use the exact values of cosine and sine.")
        facts.update(z=z, n=n, r=r, theta=theta)
        label = f"z{_sup(n)}"
    elif task == "roots":
        w = canon(parse_math(p.given["w"], imaginary=True))
        n = int(p.given["n"])
        r, theta = polar_steps(B, w)
        roots = []
        for k in range(n):
            ang = (theta + 2 * sp.pi * k) / n
            formula = _m(sp.Pow(r, sp.Rational(1, n), evaluate=False),
                         _a(sp.cos(ang, evaluate=False), _m(I, sp.sin(ang, evaluate=False))))
            B.add(formula, f"Root k = {k}", formula,
                  f"z_k = r^(1/{n})·(cos((θ + 2πk)/{n}) + i sin((θ + 2πk)/{n})) with k = {k}: angle {to_text(ang)}.",
                  kind=FACT, fact="root_formula", k=k)
            val = canon(sp.root(r, n) * (sp.cos(ang) + I * sp.sin(ang)))
            B.add(formula, f"z{sub(k)} in a + bi form", val, "Evaluate cos and sin exactly.")
            roots.append(val)
        facts.update(w=w, n=n, r=r, theta=theta, roots=roots)
        answer, label = roots, f"the {n} roots"
    elif task == "quadratic":
        a, b, c = (parse_math(p.given[k]) for k in ("a", "b", "c"))
        disc = b**2 - 4 * a * c
        B.add(_a(sp.Pow(b, 2, evaluate=False), _m(-4, a, c)), "Discriminant Δ = b² − 4ac", disc,
              f"a = {to_text(a)}, b = {to_text(b)}, c = {to_text(c)}.")
        sq = sp.sqrt(disc)
        if disc < 0:
            B.add(sp.sqrt(disc, evaluate=False), "√Δ for Δ < 0", sq, f"√({to_text(disc)}) = i√{to_text(-disc)}.")
        z1 = canon((-b + sq) / (2 * a))
        z2 = canon((-b - sq) / (2 * a))
        B.add(_m(_a(-b, sq), sp.Pow(_m(2, a), -1, evaluate=False)), "z = (−b + √Δ)/(2a)", z1, "Quadratic formula, + sign.")
        B.add(_m(_a(-b, -sq), sp.Pow(_m(2, a), -1, evaluate=False)), "z = (−b − √Δ)/(2a)", z2, "Quadratic formula, − sign.")
        facts.update(a=a, b=b, c=c, disc=disc)
        answer, label = [z1, z2], "z"
        if disc < 0:
            notes.append("Δ < 0, so the two roots are complex conjugates of each other.")
    else:
        raise ProblemFormatError(f"unknown complex-number task {task!r}")
    return Solution(problem=p, steps=B.steps, answer=answer, answer_label=label, facts=facts, notes=notes)


def _reduce_angle(t):
    """Equivalent angle in (−π, π]."""
    t = sp.nsimplify(t)
    two_pi = 2 * sp.pi
    k = sp.floor((t + sp.pi) / two_pi)
    red = t - two_pi * k
    if red == -sp.pi:
        red = sp.pi
    return sp.simplify(red)


def _sup(n):
    from tutor.text.unicode_math import sup

    return sup(n)
