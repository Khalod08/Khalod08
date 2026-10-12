"""Step-by-step integration (indefinite and definite).

Like the derivative engine, the working expression keeps *unevaluated*
∫…dx nodes and each step rewrites exactly one of them with one rule:

  constant multiple, sum, power, basic antiderivatives (eˣ, sin, cos, sec²,
  1/x → ln|x|, arctan, arcsin, …), u-substitution, integration by parts,
  rewriting the integrand (algebra, trig identities, partial fractions,
  completing the square), trig substitution.

Which rule to apply comes from SymPy's ``manualintegrate.integral_steps``
(textbook-style rules). Whether the step is CORRECT is checked separately by
``tutor.verify.integrals`` by differentiation, never trusted from the rule
tree. Substitution variables (u, w, θ …) are substituted back at the end in
their own step.

Answers use ln|…| (real calculus) and are given "+ C" in the write-up.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from sympy.integrals import manualintegrate as mi

from tutor.errors import UnsupportedProblem
from tutor.steps import ALGEBRA, INTEGRAL_RULE, SETUP, Step
from tutor.text.unicode_math import to_text

U_NAMES = ["u", "w", "v", "z"]


def _I(f, x):
    return sp.Integral(f, x)


def _m(*a):
    return sp.Mul(*a, evaluate=False)


@dataclass
class Rewrite:
    rule: str             # short id
    title: str            # operation label
    replacement: sp.Expr  # expression replacing the ∫ node
    why: str
    data: dict


def _abs_logs(e: sp.Expr) -> sp.Expr:
    """ln(stuff) → ln|stuff| unless stuff is provably positive (real calculus convention)."""
    return e.replace(lambda n: isinstance(n, sp.log) and not n.args[0].is_positive and not isinstance(n.args[0], sp.Abs),
                     lambda n: sp.log(sp.Abs(n.args[0])))


def _pick(rule):
    """Resolve AlternativeRule: a direct table rule if there is one, else substitution, else the first."""
    while isinstance(rule, mi.AlternativeRule):
        direct = [r for r in rule.alternatives if isinstance(r, mi.AtomicRule)]
        subs = [r for r in rule.alternatives if isinstance(r, mi.URule)]
        rule = (direct or subs or rule.alternatives)[0]
    return rule


def rule_xreplace(rule, mapping):
    """Copy of a manualintegrate rule tree with symbols renamed (e.g. SymPy's _u → our u)."""
    import dataclasses

    if isinstance(rule, sp.Basic):
        return rule.xreplace(mapping)
    if isinstance(rule, (list, tuple)):
        return type(rule)(rule_xreplace(r, mapping) for r in rule)
    if dataclasses.is_dataclass(rule):
        changes = {f.name: rule_xreplace(getattr(rule, f.name), mapping) for f in dataclasses.fields(rule)}
        return dataclasses.replace(rule, **changes)
    return rule


class Engine:
    def __init__(self):
        self.used_names: list[sp.Symbol] = []
        self.backsubs: list[tuple[sp.Symbol, sp.Expr, str]] = []  # (u, u(x) or θ-inverse, why)
        self.plan: dict = {}  # ∫ node created by a step → the rule SymPy planned for it
        self.domain: tuple | None = None  # set when a method is only valid on part of the line

    def _expect(self, integrand, var, rule):
        if rule is not None:
            self.plan[sp.Integral(integrand, var)] = rule

    def fresh(self, base: str = "u") -> sp.Symbol:
        names = U_NAMES if base == "u" else ["θ", "φ"]
        for n in names:
            s = sp.Symbol(n, real=True)
            if s not in self.used_names:
                self.used_names.append(s)
                return s
        raise UnsupportedProblem("too many nested substitutions")

    def rewrite(self, node: sp.Integral) -> Rewrite:
        f, x = node.function, node.variables[0]
        planned = self.plan.pop(node, None)
        pf = None if planned is not None else self._partial_fractions(f, x)
        if pf is not None:
            return pf
        red = None if planned is not None else self._sec_csc_power(f, x)
        if red is not None:
            return red
        rule = planned or mi.integral_steps(f, x)
        rule = _pick(rule)
        if isinstance(rule, (mi.SqrtQuadraticRule, mi.ReciprocalSqrtQuadraticRule, mi.SqrtQuadraticDenomRule)):
            trig = mi.trig_substitution_rule(mi.IntegralInfo(f, x))  # the textbook method for √(a² ± x²)
            if isinstance(trig, mi.TrigSubstitutionRule):
                rule = trig
        return self._from_rule(rule, f, x)

    def _partial_fractions(self, f, x) -> Rewrite | None:
        """Textbook partial fractions when the denominator factors into simpler pieces."""
        if not f.is_rational_function(x) or f.is_polynomial(x):
            return None
        num, den = sp.fraction(sp.cancel(sp.together(f)))
        factors = sp.factor_list(den, x)[1]
        long_div = sp.degree(num, x) >= sp.degree(den, x)
        if len(factors) < 2 and not (factors and factors[0][1] > 1) and not long_div:
            return None
        new = sp.apart(f, x)
        if new == f or len(sp.Add.make_args(new)) < 2:
            return None
        title = "Long division + partial fractions" if long_div else "Partial fractions"
        why = (f"Factor the bottom: {to_text(sp.factor(den))}. Split into simpler fractions"
               + (" after dividing (the top's degree is not smaller than the bottom's)." if long_div else "."))
        self._expect(new, x, mi.integral_steps(new, x))
        return Rewrite("rewrite", title, _I(new, x), why, {"rewritten": new})

    def _sec_csc_power(self, f, x) -> Rewrite | None:
        """∫ secⁿ(x) and ∫ cscⁿ(x), n ≥ 3, by the reduction formula (integration by parts)."""
        if not (f.is_Pow and f.exp.is_Integer and f.exp >= 3 and f.base.args == (x,)
                and isinstance(f.base, (sp.sec, sp.csc))):
            return None
        n = int(f.exp)
        if isinstance(f.base, sp.sec):
            head = _m(sp.Pow(sp.sec(x), n - 2), sp.tan(x), sp.Pow(n - 1, -1, evaluate=False))
            fn = "sec"
        else:
            head = _m(-1, sp.Pow(sp.csc(x), n - 2), sp.cot(x), sp.Pow(n - 1, -1, evaluate=False))
            fn = "csc"
        rep = sp.Add(head, _m(sp.Rational(n - 2, n - 1), _I(f.base ** (n - 2), x)), evaluate=False)
        return Rewrite("reduction", "Reduction formula (integration by parts)", rep,
                       f"Integrate by parts with u = {fn}^{n - 2}(x), dv = {fn}²(x) dx, then use "
                       f"{'tan² = sec² − 1' if fn == 'sec' else 'cot² = csc² − 1'} and solve for the integral: "
                       f"∫{fn}ⁿ = {'' if fn == 'sec' else '−'}{fn}ⁿ⁻²·{'tan' if fn == 'sec' else 'cot'}/(n − 1) + "
                       f"(n − 2)/(n − 1)·∫{fn}ⁿ⁻².", {"n": n})

    def _from_rule(self, rule, f, x) -> Rewrite:
        t = to_text
        R = mi
        if isinstance(rule, R.DontKnowRule) or rule is None:
            raise UnsupportedProblem(f"the verified integrator doesn't know a textbook method for ∫ {t(f)} d{x}")
        if isinstance(rule, R.ConstantRule):
            return Rewrite("constant", "Integral of a constant", _m(f, x), f"∫ c d{x} = c·{x}.", {})
        if isinstance(rule, R.ConstantTimesRule):
            self._expect(rule.other, x, rule.substep)
            return Rewrite("constant_multiple", "Constant multiple rule", _m(rule.constant, _I(rule.other, x)),
                           f"Pull the constant {t(rule.constant)} out of the integral.", {"constant": rule.constant})
        if isinstance(rule, R.AddRule):
            terms = [s.integrand for s in rule.substeps]
            for s_ in rule.substeps:
                self._expect(s_.integrand, x, s_)
            return Rewrite("sum", "Sum rule", sp.Add(*[_I(term, x) for term in terms], evaluate=False),
                           "Integrate term by term.", {"terms": terms})
        if isinstance(rule, R.PowerRule):
            b, n = rule.base, rule.exp
            if n == -1:
                return Rewrite("log", "∫ 1/u du = ln|u|", sp.log(sp.Abs(b)), f"∫ 1/{t(b)} d{x} = ln|{t(b)}|.", {})
            if b != x:
                raise UnsupportedProblem("unexpected power rule form")
            rep = _m(sp.Pow(x, n + 1), sp.Pow(n + 1, -1, evaluate=False)) if n + 1 != 1 else x
            return Rewrite("power", "Power rule", rep,
                           f"∫ {x}ⁿ d{x} = {x}ⁿ⁺¹/(n + 1) with n = {t(n)}: raise the power by 1 and divide by the new power.",
                           {"exponent": n})
        if isinstance(rule, R.ReciprocalRule):
            b = rule.base
            return Rewrite("log", "∫ 1/u du = ln|u|", sp.log(sp.Abs(b)), f"∫ 1/{t(b)} d{x} = ln|{t(b)}|.", {})
        if isinstance(rule, R.ExpRule):
            val = rule.eval()
            why = f"∫ e^{x} d{x} = e^{x}." if rule.base == sp.E else f"∫ aˣ dx = aˣ/ln(a) with a = {t(rule.base)}."
            return Rewrite("exp", "Exponential rule", val, why, {})
        basic = {R.SinRule: "∫ sin = −cos", R.CosRule: "∫ cos = sin", R.Sec2Rule: "∫ sec² = tan",
                 R.SecTanRule: "∫ sec·tan = sec", R.CscCotRule: "∫ csc·cot = −csc", R.Csc2Rule: "∫ csc² = −cot",
                 R.ArcsinRule: "∫ 1/√(1 − x²) = arcsin x", R.SinhRule: "∫ sinh = cosh", R.CoshRule: "∫ cosh = sinh"}
        for cls, title in basic.items():
            if isinstance(rule, cls):
                return Rewrite("basic", "Basic antiderivative", rule.eval(), f"Standard antiderivative: {title}.", {})
        if isinstance(rule, R.ArctanRule):
            return Rewrite("arctan", "Arctangent form", rule.eval(),
                           "∫ 1/(a² + x²) dx = (1/a)·arctan(x/a).", {})
        if isinstance(rule, (R.ReciprocalSqrtQuadraticRule, R.SqrtQuadraticRule, R.SqrtQuadraticDenomRule)):
            return Rewrite("table", "Standard form", _abs_logs(rule.eval()),
                           "A standard integral of a square root of a quadratic.", {})
        if isinstance(rule, R.URule):
            u = self.fresh("u")
            sub = rule_xreplace(rule.substep, {rule.u_var: u})
            g = sub.integrand
            self._expect(g, u, sub)
            du = sp.diff(rule.u_func, x)
            self.backsubs.append((u, rule.u_func, "u-substitution"))
            return Rewrite("substitution", "u-substitution", _I(g, u),
                           f"Let {u} = {t(rule.u_func)}, so d{u} = {t(du)} d{x}. Rewrite everything in terms of {u}.",
                           {"u": u, "u_func": rule.u_func, "du": du, "x": x, "g": g})
        if isinstance(rule, R.PartsRule):
            uu, dv = rule.u, rule.dv
            v = _abs_logs(rule.v_step.eval())
            du = sp.diff(uu, x)
            second = rule.second_step
            vdu = second.integrand if second is not None and second.integrand is not None else sp.expand(v * du)
            self._expect(vdu, x, second if second is not None and second.integrand is not None else None)
            rep = sp.Add(_m(uu, v), _m(-1, _I(vdu, x)), evaluate=False)
            return Rewrite("parts", "Integration by parts", rep,
                           f"∫ u dv = uv − ∫ v du with u = {t(uu)}, dv = {t(dv)} d{x}; then du = {t(du)} d{x} and "
                           f"v = {t(v)}.", {"u": uu, "dv": dv, "v": v, "du": du})
        if isinstance(rule, R.CyclicPartsRule):
            val = _abs_logs(rule.eval())
            first, second = rule.parts_rules[0], rule.parts_rules[1]
            return Rewrite("cyclic_parts", "Integration by parts twice", val,
                           f"Use parts twice (u = {t(first.u)}, then u = {t(second.u)}). The original integral I "
                           f"comes back, so solve the equation for I.", {})
        if isinstance(rule, R.RewriteRule):
            new = rule.rewritten
            self._expect(new, x, rule.substep)
            if isinstance(rule, R.CompleteSquareRule):
                title, why = "Complete the square", "Complete the square in the denominator."
            elif f.is_rational_function(x) and _is_partial_fractions(f, new, x):
                title, why = "Partial fractions", "Split the rational function into partial fractions."
            elif f.has(sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot):
                title, why = "Trig identity", "Rewrite the integrand with a trigonometric identity."
            else:
                title, why = "Rewrite the integrand", "Rewrite the integrand algebraically (expand / simplify)."
            return Rewrite("rewrite", title, _I(new, x), why, {"rewritten": new})
        if isinstance(rule, R.TrigSubstitutionRule):
            th = self.fresh("θ")
            func = rule.func.xreplace({rule.theta: th})
            rewritten = rule.rewritten.xreplace({rule.theta: th})
            self._expect(rewritten, th, rule_xreplace(rule.substep, {rule.theta: th}))
            coef, trig = func.as_independent(th, as_Add=False)
            inverse = {sp.sin: sp.asin, sp.tan: sp.atan, sp.sec: sp.asec}.get(type(trig))
            if inverse is None or trig.args != (th,):
                raise UnsupportedProblem(f"unexpected trig substitution {t(func)}")
            back = inverse(x / coef)  # principal branch: θ in (−π/2, π/2), or [0, π/2) for sec
            if type(trig) is sp.sec:
                self.domain = (sp.Abs(coef), sp.oo)  # x = a·sec θ with 0 ≤ θ < π/2 means x ≥ a
            rng = "−π/2 < θ < π/2" if type(trig) is not sp.sec else "0 ≤ θ < π/2"
            self.backsubs.append((th, back, "trig substitution"))
            return Rewrite("trig_sub", "Trig substitution", _I(rewritten, th),
                           f"Let {x} = {t(func)} with {rng}, so d{x} = {t(sp.diff(func, th))} dθ. Simplify the "
                           f"root with a Pythagorean identity (cos θ > 0 on this range).",
                           {"theta": th, "func": func, "x": x, "g": rewritten, "trig": type(trig).__name__})
        if isinstance(rule, R.AtomicRule):
            return Rewrite("table", "Standard antiderivative", _abs_logs(rule.eval()), "A standard antiderivative.", {})
        raise UnsupportedProblem(f"the verified integrator can't show steps for ∫ {t(f)} d{x} yet")


def _is_partial_fractions(f, new, x) -> bool:
    num, den = sp.fraction(sp.together(f))
    return den.has(x) and sp.Poly(den, x).degree() >= 2 and len(sp.Add.make_args(sp.expand(new))) >= 2


def first_integral(expr) -> sp.Integral | None:
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.Integral) and all(len(lim) == 1 for lim in node.limits):
            return node
    return None


def _rebuild(e):
    if not e.args or isinstance(e, (sp.Integral,)):
        return e
    return e.func(*[_rebuild(a) for a in e.args])


def antiderivative_steps(f: sp.Expr, x: sp.Symbol, k: int = 1, prefix: str = "s",
                         max_steps: int = 120, info: dict | None = None) -> tuple[list[Step], sp.Expr]:
    """Steps from ∫ f dx to an antiderivative F (no + C). Returns (steps, F).

    If ``info`` is a dict, ``info["domain"]`` is set when the method only holds on an
    interval (e.g. x = a·sec θ needs x ≥ a)."""
    eng = Engine()
    steps: list[Step] = []
    cur: sp.Expr = _I(f, x)
    while (node := first_integral(cur)) is not None:
        if len(steps) > max_steps:
            raise UnsupportedProblem("integration needed too many steps; refusing to guess")
        rw = eng.rewrite(node)
        with sp.evaluate(False):
            after = cur.xreplace({node: rw.replacement})
        steps.append(Step(id=f"{prefix}{k}", kind=INTEGRAL_RULE, before=cur, operation=rw.title, after=after,
                          justification=rw.why,
                          data={"rule": rw.rule, "target": node, "replacement": rw.replacement, **rw.data}))
        cur, k = after, k + 1
        # Undo substitutions innermost-first (a stack): the most recent variable can be
        # substituted back once no integral in it is left.
        while eng.backsubs:
            u, back, why = eng.backsubs[-1]
            if any(isinstance(n, sp.Integral) and n.has(u) for n in sp.preorder_traversal(cur)):
                break
            if cur.has(u):
                new = _rebuild(cur.xreplace({u: back}))
                new = sp.simplify(new) if why == "trig substitution" else new
                steps.append(Step(id=f"{prefix}{k}", kind=INTEGRAL_RULE, before=cur,
                                  operation=f"Substitute back {u} = {to_text(back)}", after=new,
                                  justification=("Write the answer in terms of the original variable."
                                                 + (" Simplify trig of inverse trig with a right triangle."
                                                    if why == "trig substitution" else "")),
                                  data={"rule": "back_substitute", "u": u, "back": back}))
                cur, k = new, k + 1
            eng.backsubs.pop()
            eng.used_names.remove(u)
    if info is not None:
        info["domain"] = eng.domain
    F = _rebuild(cur)
    if F != cur:
        steps.append(Step(id=f"{prefix}{k}", kind=ALGEBRA, before=cur, operation="Simplify", after=F,
                          justification="Combine the constants.", data={}))
        k += 1
    nicer = sp.expand(F) if F.is_polynomial(x) else F
    if nicer != F and sp.count_ops(nicer) < sp.count_ops(F):
        steps.append(Step(id=f"{prefix}{k}", kind=ALGEBRA, before=F, operation="Expand", after=nicer,
                          justification="Multiply out.", data={}))
        F = nicer
    return steps, F


def integral_setup(f, x) -> Step:
    return Step(id="s0", kind=SETUP, before=f, operation="Set up", after=_I(f, x),
                justification=f"We want an antiderivative of {to_text(f)}.", data={"variable": x})
