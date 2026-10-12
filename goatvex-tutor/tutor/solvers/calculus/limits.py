"""Limits, step by step (Mingarelli 2.1–2.5, 3.8–3.9).

Methods, tried in the order a student would:
  1. direct substitution (the function is continuous at a)
  2. factor and cancel (0/0 for rational functions)
  3. multiply by the conjugate (0/0 or ∞ − ∞ with square roots)
  4. divide by the highest power of x (x → ±∞)
  5. L'Hôpital's rule (0/0 or ∞/∞), including 0·∞ rewritten as a quotient
  6. nonzero/0: an infinite limit; sign from each side; two-sided may not exist
  7. 1^∞, 0⁰, ∞⁰: take ln, find that limit, exponentiate

Each rewrite keeps the function the same near a (checked by the verifier);
the answer is checked against SymPy and by evaluating f closer and closer to a.
"""

from __future__ import annotations

import mpmath
import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem, parse_math
from tutor.solvers.builder import Builder
from tutor.steps import FACT, LIMIT_STEP, SETUP, Solution, Step
from tutor.text.unicode_math import to_text

DNE = sp.Symbol("DNE")


def L(g, x, a, d):
    return sp.Limit(g, x, a, d)


def _frac(n, d):
    return sp.Mul(n, sp.Pow(d, -1, evaluate=False), evaluate=False)


def has_root(e) -> bool:
    return any(p.is_Pow and p.exp.is_Rational and not p.exp.is_Integer for p in sp.preorder_traversal(e))


def num_den(g):
    """Top and bottom as written (an unevaluated a·b⁻¹ keeps its parts), else via together()."""
    if isinstance(g, sp.Mul):
        inv = [f for f in g.args if f.is_Pow and f.exp == -1]
        if len(inv) == 1:
            rest = [f for f in g.args if f is not inv[0]]
            return sp.Mul(*rest), inv[0].base
    return sp.fraction(sp.together(g))


def continuous_at(g, x, a, d) -> bool:
    try:
        dom = sp.calculus.util.continuous_domain(g, x, sp.S.Reals)
    except Exception:
        return False
    if d == "+-":
        return dom.contains(a) == sp.true and dom.contains(a - sp.Rational(1, 10**6)) == sp.true \
            and dom.contains(a + sp.Rational(1, 10**6)) == sp.true
    side = a + sp.Rational(1, 10**6) if d == "+" else a - sp.Rational(1, 10**6)
    return dom.contains(a) == sp.true and dom.contains(side) == sp.true


def side_sign(expr, x, a, d) -> int:
    """Sign of expr just to one side of a (numerically, 60 digits)."""
    f = sp.lambdify(x, expr, "mpmath")
    with mpmath.workdps(60):
        h = mpmath.mpf(10) ** -12
        v = f(mpmath.mpf(sp.N(a, 70)) + (h if d == "+" else -h))
        return 1 if mpmath.re(v) > 0 else -1


class LimitSolver:
    def __init__(self, x, a, d):
        self.x, self.a, self.d = x, a, d
        self.B = Builder()
        self.notes: list[str] = []

    def step(self, g_before, g_after, op, why, rule, **data):
        return self.B.add(L(g_before, self.x, self.a, self.d), op, L(g_after, self.x, self.a, self.d), why,
                          kind=LIMIT_STEP, chain=True, rule=rule, x=self.x, a=self.a, dir=self.d, **data)

    def solve(self, g, depth: int = 0):
        x, a, d = self.x, self.a, self.d
        if depth > 10:
            raise UnsupportedProblem("this limit needs more steps than the verified solver allows")
        if g.has(sp.Abs) and d in ("+", "-") and not a.is_infinite:
            return self._remove_abs(g, depth)
        if a.is_infinite:
            done = self._at_infinity_direct(g)
            if done is not None:
                return done
        # 1. direct substitution
        if not a.is_infinite and continuous_at(g, x, a, d):
            with sp.evaluate(False):
                shown = g.xreplace({x: a})
            val = sp.simplify(g.subs(x, a))
            self.B.add(L(g, x, a, d), "Direct substitution", shown,
                       f"The function is continuous at {x} = {to_text(a)}, so substitute {x} = {to_text(a)}.",
                       kind=LIMIT_STEP, chain=True, rule="substitute", x=x, a=a, dir=d, g=g)
            return self.B.add(shown, "Arithmetic", val, "Simplify.", chain=True)
        num, den = num_den(g)
        ln_, ld_ = (sp.limit(num, x, a, d if d != "+-" else "+"), sp.limit(den, x, a, d if d != "+-" else "+"))
        if not a.is_infinite and ln_ == 0 and ld_ == 0:
            return self._zero_over_zero(g, num, den, depth)
        if a.is_infinite and den != 1 and ln_.is_infinite and ld_.is_infinite:
            if g.is_rational_function(x):
                return self._divide_highest_power(g, num, den, depth)
            if has_root(num) or has_root(den):
                return self._divide_highest_power_roots(g, num, den, depth)
            return self._lhospital(g, num, den, depth, "∞/∞")
        if a.is_infinite and den != 1 and g.is_rational_function(x):
            return self._divide_highest_power(g, num, den, depth)
        if not a.is_infinite and ld_ == 0 and ln_ != 0 and ln_.is_finite:
            return self._infinite(g, num, den, ln_)
        # other indeterminate forms
        if g.is_Pow and g.exp.has(x) and g.base.has(x):
            return self._exponent_form(g, depth)
        if g.is_Mul and den == 1:
            factors = g.as_ordered_factors()
            lims = [sp.limit(fct, x, a, d if d != "+-" else "+") for fct in factors]
            zeros = [fct for fct, lv in zip(factors, lims) if lv == 0]
            infs = [fct for fct, lv in zip(factors, lims) if lv.is_infinite]
            if zeros and infs:
                z = sp.Mul(*zeros)
                inf = sp.Mul(*[fct for fct in factors if fct not in zeros])
                algebraic = lambda e: e.is_polynomial(x) or (e.is_Pow and e.base == x)  # noqa: E731
                if algebraic(inf) and not algebraic(z):
                    top, bottom, form = z, sp.Pow(inf, -1), "0/0"   # e.g. x·ln(1 + 2/x) = ln(1 + 2/x)/(1/x)
                else:
                    top, bottom, form = inf, sp.Pow(z, -1), "∞/∞"   # e.g. x·ln x = ln x/(1/x)
                new = _frac(top, bottom)
                self.step(g, new, "Rewrite 0·∞ as a quotient",
                          f"A product of the form 0·∞ is indeterminate. Write it as a quotient of the form {form} "
                          "so L'Hôpital's rule can be used.", "rewrite")
                return self._lhospital(new, top, bottom, depth, form)
        if g.is_Add and any(has_root(t) for t in g.args):
            return self._conjugate(g, g, sp.Integer(1), depth)
        if g.is_Add and den != 1:
            combined = sp.together(g)
            if combined != g:
                self.step(g, combined, "Combine into one fraction", "Use a common denominator.", "rewrite")
                return self.solve(combined, depth + 1)
        laws = self._limit_laws(g)
        if laws is not None:
            return laws
        if a.is_infinite and den != 1 and (has_root(num) or has_root(den)):
            return self._divide_highest_power_roots(g, num, den, depth)
        raise UnsupportedProblem(f"the verified limit solver has no textbook method for lim {to_text(g)} yet")

    # ---------------------------------------------------------------- extra methods
    def _at_infinity_direct(self, g):
        """x → ±∞: if g is continuous in t = 1/x at t = 0, every c/xⁿ → 0 and we can evaluate."""
        x, a = self.x, self.a
        t = sp.Symbol("t_", positive=True)
        h = g.xreplace({x: (1 if a == sp.oo else -1) / t})
        try:
            if not continuous_at(sp.simplify(h), t, sp.Integer(0), "+"):
                return None
            val = sp.limit(h, t, 0, "+")
        except Exception:
            return None
        if not val.is_finite or g.has(sp.sin, sp.cos, sp.tan):
            return None
        if not any(p.is_Pow and p.base == x and p.exp.is_negative for p in sp.preorder_traversal(g)) and g.has(x):
            return None
        shown = g.replace(lambda e: e.is_Pow and e.base == x and e.exp.is_negative, lambda e: sp.Integer(0))
        self.B.add(L(g, x, a, self.d), f"Each c/{x}ⁿ → 0", val,
                   f"As {x} → {to_text(a)}, every term with {x} in a denominator goes to 0.",
                   kind=LIMIT_STEP, chain=True, rule="term_limits", x=x, a=a, dir=self.d, g=g)
        return val

    def _limit_laws(self, g):
        """No indeterminate form: combine the limits of the pieces (sums, products, quotients)."""
        x, a, d = self.x, self.a, self.d
        side = d if d != "+-" else "+"
        if not (g.is_Add or g.is_Mul or g.is_Pow or isinstance(g, sp.Function)):
            return None
        pieces = sp.Add.make_args(g) if g.is_Add else sp.Mul.make_args(g) if g.is_Mul else (g,)
        lims = [sp.limit(pc, x, a, side) for pc in pieces]
        if any(v.has(sp.AccumBounds) or v == sp.nan for v in lims):
            return None
        if g.is_Add and sp.oo in lims and -sp.oo in lims:
            return None
        if g.is_Mul and any(v == 0 for v in lims) and any(v.is_infinite for v in lims):
            return None
        val = sp.limit(g, x, a, side)
        if d == "+-" and not a.is_infinite and sp.limit(g, x, a, "-") != val:
            return None
        desc = "; ".join(f"{to_text(pc)} → {to_text(v)}" for pc, v in zip(pieces, lims))
        self.B.add(L(g, x, a, d), "Limit laws", val,
                   f"No indeterminate form here: {desc}. Combine them.", kind=LIMIT_STEP, chain=True,
                   rule="evaluate", x=x, a=a, dir=d, g=g)
        return val

    def _remove_abs(self, g, depth):
        """One-sided limit: near a on this side each |h| is just h or −h."""
        x, a, d = self.x, self.a, self.d
        reps, desc = {}, []
        for ab in g.atoms(sp.Abs):
            h = ab.args[0]
            sgn = side_sign(h, x, a, d)
            reps[ab] = h if sgn > 0 else -h
            desc.append(f"|{to_text(h)}| = {'' if sgn > 0 else '−'}({to_text(h)})")
        new = g.xreplace(reps)
        width = sp.Rational(1, 2)
        dom = (a, a + width) if d == "+" else (a - width, a)
        self.step(g, new, "Remove the absolute value",
                  f"For {x} just {'above' if d == '+' else 'below'} {to_text(a)}: " + ", ".join(desc) + ".",
                  "rewrite", domain=dom)
        return self.solve(new, depth + 1)

    def _divide_highest_power_roots(self, g, num, den, depth):
        x, a = self.x, self.a
        k = sp.limit(sp.log(sp.Abs(den)) / sp.log(sp.Abs(x)), x, a)
        if not (k.is_Rational and k > 0):
            raise UnsupportedProblem(f"the verified limit solver has no textbook method for lim {to_text(g)} yet")
        p_ = sp.Symbol("p_", positive=True)
        sgn = 1 if a == sp.oo else -1
        top = sp.simplify((num / x**k).xreplace({x: sgn * p_})).xreplace({p_: sgn * x})
        bot = sp.simplify((den / x**k).xreplace({x: sgn * p_})).xreplace({p_: sgn * x})
        new = _frac(top, bot)
        self.step(g, new, f"Divide top and bottom by {to_text(x**k)}",
                  f"{to_text(x**k)} is the dominant power in the bottom. Inside a root, dividing by {x} means "
                  f"dividing by {x}² under the square root (for {x} {'> 0' if sgn > 0 else '< 0'}).", "rewrite",
                  domain=(sp.Integer(1), sp.oo) if sgn > 0 else (-sp.oo, sp.Integer(-1)))
        return self.solve(new, depth + 1)

    def _zero_over_zero(self, g, num, den, depth):
        x, a = self.x, self.a
        if g.is_rational_function(x):
            fn, fd = sp.factor(num), sp.factor(den)
            factored = _frac(fn, fd)
            self.step(g, factored, "Factor", f"Substituting {x} = {to_text(a)} gives 0/0, an indeterminate form. "
                      f"Factor the top and the bottom.", "rewrite")
            cancelled = sp.cancel(fn / fd)
            common = sp.factor(sp.gcd(num, den))
            self.step(factored, cancelled, f"Cancel {to_text(common)}",
                      f"For {x} ≠ {to_text(a)} the common factor {to_text(common)} is not 0, so it cancels. "
                      f"The limit only looks at {x} near {to_text(a)}, not at {to_text(a)}.", "rewrite",
                      cancelled_factor=common)
            return self.solve(cancelled, depth + 1)
        if has_root(num) or has_root(den):
            return self._conjugate(g, num, den, depth)
        return self._lhospital(g, num, den, depth, "0/0")

    def _conjugate(self, g, num, den, depth):
        x, a = self.x, self.a
        target = num if has_root(num) else den
        terms = sp.Add.make_args(target)
        rad = [t for t in terms if has_root(t)]
        if len(terms) != 2 or not rad:
            return self._lhospital(g, num, den, depth, "0/0")
        first, second = (terms[0], terms[1]) if not has_root(terms[0]) or len(rad) == 2 else (terms[1], terms[0])
        conj = second - first if first.could_extract_minus_sign() else first - second  # e.g. √(x+4) + 2
        new = _frac(sp.Mul(num, conj, evaluate=False), sp.Mul(den, conj, evaluate=False))
        self.step(g, new, "Multiply by the conjugate", f"Multiply top and bottom by the conjugate {to_text(conj)} "
                  f"to clear the square root ((A + B)(A − B) = A² − B²).", "rewrite", conjugate=conj)
        simpler = sp.cancel(sp.expand(num * conj) / sp.expand(den * conj))
        tidy = sp.factor(simpler) if simpler.is_rational_function(x) else sp.simplify(simpler)
        self.step(new, tidy, "Simplify", "Multiply out the product A² − B² and cancel common factors.", "rewrite")
        return self.solve(tidy, depth + 1)

    def _divide_highest_power(self, g, num, den, depth):
        x = self.x
        k = sp.degree(den, x)
        p = x**k
        n_terms = [sp.simplify(t / p) for t in sp.Add.make_args(sp.expand(num))]
        d_terms = [sp.simplify(t / p) for t in sp.Add.make_args(sp.expand(den))]
        new = _frac(sp.Add(*n_terms, evaluate=False), sp.Add(*d_terms, evaluate=False))
        self.step(g, new, f"Divide top and bottom by {to_text(p)}",
                  f"{to_text(p)} is the highest power of {x} in the denominator.", "rewrite", divisor=p)
        limits = [sp.limit(t, x, self.a) for t in n_terms + d_terms]
        vals_n = [sp.limit(t, x, self.a) for t in n_terms]
        vals_d = [sp.limit(t, x, self.a) for t in d_terms]
        if any(v.is_infinite for v in limits):
            # degree of top > degree of bottom: the limit is infinite
            res = sp.limit(g, x, self.a)
            return self._finish_infinite_at_infinity(new, res)
        shown = _frac(sp.Add(*vals_n, evaluate=False), sp.Add(*vals_d, evaluate=False))
        self.B.add(L(new, x, self.a, self.d), f"Each c/{x}ⁿ → 0", shown,
                   f"As {x} → {to_text(self.a)}, every term c/{x}ⁿ with n ≥ 1 goes to 0.",
                   kind=LIMIT_STEP, chain=True, rule="term_limits", x=x, a=self.a, dir=self.d, g=new)
        return self.B.add(shown, "Arithmetic", sp.Add(*vals_n) / sp.Add(*vals_d), "Simplify.", chain=True)

    def _finish_infinite_at_infinity(self, new, res):
        self.B.add(L(new, self.x, self.a, self.d), "The top grows without bound", res,
                   "The top has a higher power than the bottom, so the quotient grows without bound; the sign comes "
                   "from the leading terms.", kind=LIMIT_STEP, chain=True, rule="evaluate", x=self.x, a=self.a,
                   dir=self.d, g=new)
        return res

    def _lhospital(self, g, num, den, depth, form):
        x = self.x
        dn, dd = sp.diff(num, x), sp.diff(den, x)
        new = _frac(dn, dd)
        self.step(g, new, "L'Hôpital's rule",
                  f"The form is {form}, so lim f/g = lim f′/g′ (differentiate the top and the bottom separately): "
                  f"({to_text(num)})′ = {to_text(dn)} and ({to_text(den)})′ = {to_text(dd)}.", "lhospital",
                  num=num, den=den, form=form)
        tidy = sp.simplify(dn / dd)
        if tidy != new:
            self.step(new, tidy, "Simplify", "Simplify before taking the limit again.", "rewrite")
            return self.solve(tidy, depth + 1)
        return self.solve(new, depth + 1)

    def _infinite(self, g, num, den, top):
        x, a, d = self.x, self.a, self.d
        sides = ["+", "-"] if d == "+-" else [d]
        results = {}
        for sd in sides:
            s_den = side_sign(den, x, a, sd)
            results[sd] = sp.oo if (s_den > 0) == (top > 0) else -sp.oo
        desc = "; ".join(f"from the {'right' if sd == '+' else 'left'} the bottom → 0"
                         f"{'⁺' if side_sign(den, x, a, sd) > 0 else '⁻'}, so f → {to_text(results[sd])}"
                         for sd in sides)
        if d == "+-" and results["+"] != results["-"]:
            res = DNE
            self.notes.append(f"Right-hand limit {to_text(results['+'])}, left-hand limit {to_text(results['-'])}: "
                              "they differ, so the two-sided limit does not exist.")
        else:
            res = results[sides[0]]
        self.B.add(L(g, x, a, d), "Nonzero over zero", res,
                   f"The top → {to_text(top)} ≠ 0 and the bottom → 0: an infinite limit. {desc}.",
                   kind=LIMIT_STEP, chain=True, rule="infinite", x=x, a=a, dir=d, g=g, sides=results)
        return res

    def _exponent_form(self, g, depth):
        x, a, d = self.x, self.a, self.d
        base, ex = g.base, g.exp
        lny = ex * sp.log(base)
        self.B.add(L(g, x, a, d), "Take ln", L(lny, x, a, d),
                   f"For a limit of the form 1^∞, 0⁰ or ∞⁰ let y = {to_text(g)}; then ln y = {to_text(lny)}. "
                   "Find lim ln y first.", kind=FACT, chain=False, rule="take_log")
        inner = LimitSolver(x, a, d)
        inner.B = Builder(start=self.B.k)
        val = inner.solve(lny, depth + 1)
        for s_ in inner.B.steps:
            s_.data["in_log"] = True
        inner.B.steps[0].data["chain"] = False
        self.B.steps += inner.B.steps
        self.B.k = inner.B.k
        res = sp.exp(val)
        self.B.add(sp.exp(sp.Symbol("ℓ")), "Exponentiate", res, f"lim ln y = {to_text(val)}, so lim y = e^({to_text(val)}).",
                   kind=FACT, chain=False, rule="exponentiate")
        return res


def _simple_infinite(f, x, a) -> bool:
    """nonzero/0 cases are handled (both sides) by the 'Nonzero over zero' step itself."""
    num, den = sp.fraction(sp.together(f))
    return not f.has(sp.Abs) and sp.limit(den, x, a) == 0 and sp.limit(num, x, a) not in (0,) \
        and sp.limit(num, x, a).is_finite


def solve(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("function")
    a = parse_math(p.given["point"])
    d = p.given.get("direction", "+-")
    if d not in ("+-", "+", "-"):
        raise ProblemFormatError("direction must be '+-' (two-sided), '+' (from the right) or '-' (from the left)")
    if a.is_infinite:
        d = "-" if a == sp.oo else "+"
    S = LimitSolver(x, a, d)
    S.B.steps.append(Step(id="s0", kind=SETUP, before=f, operation="Set up", after=L(f, x, a, d),
                          justification=f"Find the limit as {x} → {to_text(a)}"
                                        + ("" if d == "+-" or a.is_infinite else
                                           (" from the right" if d == "+" else " from the left")) + ".",
                          data={"chain": False}))
    left = right = None
    if d == "+-" and not a.is_infinite and (f.has(sp.Abs) or sp.limit(f, x, a, "+") != sp.limit(f, x, a, "-")) \
            and not _simple_infinite(f, x, a):
        # The two sides behave differently: find each one-sided limit separately.
        for side, name in (("+", "right"), ("-", "left")):
            sub = LimitSolver(x, a, side)
            sub.B = Builder(start=S.B.k)
            sub.B.add(f, f"{name.capitalize()}-hand limit", L(f, x, a, side),
                      f"Find the limit as {x} → {to_text(a)} from the {name}.", kind=SETUP, chain=False)
            val = sub.solve(f)
            S.B.steps += sub.B.steps
            S.B.k = sub.B.k
            S.notes += sub.notes
            if side == "+":
                right = val
            else:
                left = val
        value = right if left == right else DNE
        S.B.add(None, "Compare the two sides", value,
                f"Right-hand limit = {to_text(right)}, left-hand limit = {to_text(left)}: "
                + ("they agree." if left == right else "they differ, so the two-sided limit does not exist."),
                kind=FACT, chain=False, rule="compare")
    else:
        value = S.solve(f)
    if value == DNE:
        label = "the limit does not exist"
    else:
        label = "limit"
    return Solution(problem=p, steps=S.B.steps, answer=value, answer_label=label,
                    facts={"function": f, "variable": x, "point": a, "direction": d}, notes=S.notes)
