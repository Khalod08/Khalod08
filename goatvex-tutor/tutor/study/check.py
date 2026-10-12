"""/check: go through the student's own work line by line and find the first wrong line.

The student's work is transcribed (by GoatVex, confirmed by the student) into
plain text, one step per line:

    matrices    1 2 3; 0 1 4        (rows separated by ';')
    algebra     f'(x) = 3x^2 cos(x^3) = ...

Every line is compared with VERIFIED data by the same equivalence checker the
solver uses (symbolic proof + random numeric points):

* row reduction: each matrix must be row-equivalent to the one before (and is
  ideally exactly one elementary row operation away)
* derivatives and other "the answer is an expression" problems: every line
  must equal the verified answer
* antiderivatives: every line's derivative must equal the integrand
* limits: every expression must equal the one before (near the point), and
  every number must equal the verified limit
* numbers (determinants, definite integrals, areas …): every number must equal
  the verified answer

The first line that fails is the first wrong line. GoatVex then tries a few
named mistakes (sign error, missing inner derivative, product/quotient rule
slips, a row operation done with the wrong sign …) and reports the one that
explains the line exactly. If none does, it says "algebra/arithmetic error"
rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp

from tutor import registry
from tutor.text.unicode_math import matrix_text, to_text
from tutor.types._answers import normalize, parse_answer_expr, parse_answer_matrix
from tutor.verify.equivalence import check_equal
from tutor.verify.result import FAIL, PASS

EQUAL_ANSWER = {"derivative", "log_differentiation", "higher_derivative", "ftc_derivative", "inverse_function",
                "tangent_line", "linearization_line"}
ANTIDERIVATIVE = {"indefinite_integral"}
LIMITS = {"limit"}
NUMBER = {"definite_integral", "riemann_sum", "determinant", "improper_integral", "area_between_curves",
          "volume_of_revolution", "inverse_derivative", "linearization", "related_rates", "cramers_rule"}
MATRIX = {"rref", "matrix_inverse"}

LABEL = re.compile(r"^\s*(?:[A-Za-z]\w*\s*['′]*\s*(?:\(\s*[A-Za-z]\s*\))?\s*['′]*|d\s*y\s*/\s*d\s*x|y\s*['′]+|"
                   r"d/dx\s*\[.*\]|F\s*\(\s*x\s*\))\s*$")


@dataclass
class LineResult:
    n: int
    text: str
    status: str            # "ok", "wrong", "skipped"
    detail: str = ""


@dataclass
class CheckReport:
    lines: list[LineResult] = field(default_factory=list)
    first_wrong: int | None = None
    mistake: str | None = None
    explanation: str = ""
    final_correct: bool | None = None
    notes: list[str] = field(default_factory=list)
    compare_step: str = ""    # the matching verified step (not shown for graded work)

    def text(self) -> str:
        out = []
        for ln in self.lines:
            mark = {"ok": "✓", "wrong": "✗", "skipped": "·"}[ln.status]
            out.append(f"{mark} line {ln.n}: {ln.text}" + (f"    ({ln.detail})" if ln.detail else ""))
        if self.first_wrong is None:
            out.append("\nEvery line checks out." if self.final_correct else
                       "\nNo wrong line found" + (", but the work isn't finished yet." if self.final_correct is False
                                                  else "."))
        else:
            out.append(f"\nFirst wrong line: line {self.first_wrong}.")
            if self.mistake:
                out.append(f"Mistake type: {self.mistake}.")
            if self.explanation:
                out.append(self.explanation)
            if self.compare_step:
                out.append(self.compare_step)
        for n in self.notes:
            out.append("• " + n)
        return "\n".join(out)


def _eq(a, b, symbols) -> bool:
    try:
        return check_equal(a, b, symbols)[0] == PASS
    except Exception:  # noqa: BLE001
        return False


def _neq(a, b, symbols) -> bool:
    try:
        return check_equal(a, b, symbols)[0] == FAIL
    except Exception:  # noqa: BLE001
        return False


SETUP_LINE = re.compile(r"^\s*(u|v|w|t|du|dv|dw|dt|θ|x)\s*=", re.I)


def split_entries(line: str) -> list[str]:
    """'f'(x) = 3x^2 + 1 = ...' → ['3x^2 + 1', ...] (labels such as f'(x), dy/dx, y' dropped)."""
    parts = [p.strip() for p in normalize(line).split("=")]
    return [p for p in parts if p and not LABEL.match(p)]


# ----------------------------------------------------------------- expression mistakes
def _inner_derivatives(f, x):
    out = []
    for node in sp.preorder_traversal(f):
        inner = None
        if isinstance(node, sp.Function) and node.args:
            inner = node.args[0]
        elif isinstance(node, sp.Pow) and node.base != x:
            inner = node.base if node.base.has(x) else node.exp
        if inner is not None and inner.has(x) and inner != x:
            d = sp.diff(inner, x)
            if d != 1:
                out.append((inner, d))
    return out


def classify_derivative(s, c, f, x) -> tuple[str, str]:
    sym = [x]
    num, den = sp.fraction(sp.together(f))
    if den.has(x) and num.has(x):
        nd, dd = sp.diff(num, x), sp.diff(den, x)
        if _eq(s, (num * dd - nd * den) / den ** 2, sym):
            return ("quotient rule order/sign",
                    "The two products in the numerator are in the wrong order: it's (bottom)(top)′ − (top)(bottom)′.")
        if _eq(s, nd / dd, sym):
            return "quotient rule order/sign", "The top and bottom were differentiated separately; that isn't the quotient rule."
    if _eq(s, -c, sym):
        return "sign error", "Your line is exactly the negative of the correct derivative."
    for t in sp.Add.make_args(sp.expand(c)):
        if _eq(s, c - 2 * t, sym):
            return "sign error", f"One term has the wrong sign: {to_text(t)} should appear with the opposite sign."
    for inner, d in _inner_derivatives(f, x):
        if _eq(s * d, c, sym):
            return ("forgot chain rule inner derivative",
                    f"It's missing the derivative of the inside, {to_text(inner)}, which is {to_text(d)}.")
    for g in [f]:
        factors = [a for a in sp.Mul.make_args(g) if a.has(x)]
        if g == f and len(factors) >= 2:
            u, v = factors[0], sp.Mul(*factors[1:])
            k = sp.Mul(*[a for a in sp.Mul.make_args(g) if not a.has(x)])
            du, dv = sp.diff(u, x), sp.diff(v, x)
            if _eq(s, k * du * dv, sym):
                return "product rule applied wrong", "The derivative of a product is not the product of the derivatives: (uv)′ = u′v + uv′."
            if _eq(s, k * du * v, sym) or _eq(s, k * u * dv, sym):
                return "product rule applied wrong", "One of the two product-rule terms is missing: (uv)′ = u′v + uv′."
    ratio = sp.simplify(s / c) if c != 0 else None
    if ratio is not None and ratio.is_number and ratio != 1:
        return "arithmetic error", f"Your line is {to_text(ratio)} times the correct one: a constant got lost or doubled."
    return "algebra error", "This line isn't equal to the previous one."


def classify_antiderivative(s, integrand, x) -> tuple[str, str]:
    d = sp.diff(s, x)
    sym = [x]
    if _eq(d, -integrand, sym):
        return "sign error", "Differentiating your line gives the negative of the integrand."
    ratio = sp.simplify(d / integrand)
    if ratio.is_number and ratio != 0:
        inner = [dd for _, dd in _inner_derivatives(integrand, x) if dd.is_number]
        if any(sp.simplify(ratio - q) == 0 for q in inner):
            return ("forgot to divide by the inner derivative",
                    f"Differentiating your line gives {to_text(ratio)} times the integrand: divide by the inner "
                    f"derivative {to_text(ratio)}.")
        return "arithmetic error", f"Differentiating your line gives {to_text(ratio)} times the integrand."
    return "wrong antiderivative", "Differentiating this line does not give back the integrand."


def classify_number(s, c) -> tuple[str, str]:
    if c != 0 and sp.simplify(s + c) == 0:
        return "sign error", "Right size, wrong sign."
    return "arithmetic error", "This number doesn't match the verified value."


# ----------------------------------------------------------------- matrices
def _one_op(prev: sp.Matrix, cur: sp.Matrix) -> str | None:
    """Describe the single elementary row operation taking prev to cur, if there is one."""
    from tutor.text.unicode_math import sub

    diff = [i for i in range(prev.rows) if prev.row(i) != cur.row(i)]
    if not diff:
        return "no change"
    if len(diff) == 2:
        i, j = diff
        if prev.row(i) == cur.row(j) and prev.row(j) == cur.row(i):
            return f"R{sub(i + 1)} ↔ R{sub(j + 1)}"
    if len(diff) != 1:
        return None
    r = diff[0]
    nz = [c for c in range(prev.cols) if prev[r, c] != 0]
    if nz:
        k = sp.nsimplify(cur[r, nz[0]] / prev[r, nz[0]])
        if k != 0 and cur.row(r) == k * prev.row(r):
            return f"R{sub(r + 1)} → ({to_text(k)})R{sub(r + 1)}"
    for j in range(prev.rows):
        if j == r:
            continue
        d = cur.row(r) - prev.row(r)
        nzj = [c for c in range(prev.cols) if prev[j, c] != 0]
        if nzj:
            k = d[nzj[0]] / prev[j, nzj[0]]
            if d == k * prev.row(j):
                sign = "+" if k > 0 else "−"
                return f"R{sub(r + 1)} → R{sub(r + 1)} {sign} ({to_text(abs(k))})R{sub(j + 1)}"
    return None


def _diagnose_row(prev: sp.Matrix, cur: sp.Matrix) -> tuple[str, str]:
    """A wrong matrix: find the replacement R_r → R_r + kR_j the student most likely meant."""
    from tutor.text.unicode_math import sub

    diff = [i for i in range(prev.rows) if prev.row(i) != cur.row(i)]
    if len(diff) != 1:
        return "arithmetic error in a row operation", "More than one row changed and the result isn't row-equivalent."
    r = diff[0]
    d = cur.row(r) - prev.row(r)
    best = None
    for j in range(prev.rows):
        if j == r:
            continue
        for c in range(prev.cols):
            if prev[j, c] == 0:
                continue
            k = d[c] / prev[j, c]
            intended = prev.row(r) + k * prev.row(j)
            wrong = [cc for cc in range(prev.cols) if intended[cc] != cur[r, cc]]
            if best is None or len(wrong) < len(best[2]):
                best = (j, k, wrong, intended)
    if best is None:
        return "arithmetic error in a row operation", "This row isn't a valid combination of the previous rows."
    j, k, wrong, intended = best
    sign = "+" if k > 0 else "−"
    op = f"R{sub(r + 1)} → R{sub(r + 1)} {sign} ({to_text(abs(k))})R{sub(j + 1)}"
    shown = "(" + ", ".join(to_text(e) for e in intended) + ")"
    cols = ", ".join(str(c + 1) for c in wrong)
    if all(cur[r, c] == prev[r, c] - k * prev[j, c] for c in wrong):
        return ("sign error in row reduction",
                f"It looks like you meant {op}, but subtracted where you should have added (or the other way round) "
                f"in column(s) {cols}. That operation gives row {r + 1} = {shown}.")
    return ("arithmetic error in a row operation",
            f"It looks like you meant {op}; that gives row {r + 1} = {shown}. Check column(s) {cols}.")


def _check_matrices(sol, lines, rep: CheckReport):
    start = next((s.after for s in sol.steps if isinstance(s.after, sp.MatrixBase)), None)
    answer = sol.answer if isinstance(sol.answer, sp.MatrixBase) else None
    prev = sp.Matrix(start)
    last = None
    for n, raw in lines:
        try:
            m = parse_answer_matrix(raw)
        except Exception as exc:  # noqa: BLE001
            rep.lines.append(LineResult(n, raw, "skipped", f"couldn't read it as a matrix: {exc}"))
            continue
        if m.shape != prev.shape:
            if answer is not None and m.shape == answer.shape and m == answer:
                rep.lines.append(LineResult(n, raw, "ok", "the final answer"))
                last = m
                continue
            rep.lines.append(LineResult(n, raw, "skipped", f"size {m.rows}×{m.cols} doesn't match the work"))
            continue
        if m.rref()[0] == prev.rref()[0]:
            op = _one_op(prev, m)
            detail = "" if op == "no change" else (op if op else "row-equivalent (several operations at once)")
            rep.lines.append(LineResult(n, matrix_text(m).replace("\n", "  "), "ok", detail))
            prev = m
            last = m
            continue
        mistake, why = _diagnose_row(prev, m)
        if n == lines[0][0] and m.shape == start.shape:
            mistake, why = "transcription/copying error", "The first matrix doesn't match the problem."
        rep.lines.append(LineResult(n, matrix_text(m).replace("\n", "  "), "wrong", ""))
        rep.first_wrong, rep.mistake, rep.explanation = n, mistake, why
        return
    if last is not None:
        target = answer
        if sol.problem.type == "matrix_inverse" and target is not None and last.shape != target.shape:
            nn = target.rows
            done = last[:, :nn] == sp.eye(nn)
            rep.final_correct = bool(done and last[:, nn:] == target)
        elif target is not None and last.shape == target.shape:
            rep.final_correct = last == target
        if rep.final_correct is False:
            rep.notes.append("Everything so far is correct; keep going until you reach the reduced row echelon form.")


# ----------------------------------------------------------------- expressions
def _expr_target(sol):
    ans = sol.answer
    if isinstance(ans, sp.Equality):
        ans = ans.rhs
    return ans


def _check_expressions(sol, lines, rep: CheckReport, raw_text: str):
    p = sol.problem
    t = p.type
    x = sp.Symbol(p.given.get("variable", "x"), real=True)
    variables = [str(x)] + (["y"] if t == "implicit_derivative" else [])
    syms = [x] + ([sp.Symbol("y", real=True)] if t == "implicit_derivative" else [])
    target = _expr_target(sol)
    integrand = p.expr("integrand") if "integrand" in p.given and t in ANTIDERIVATIVE | {"definite_integral"} else None
    f = p.function if "function" in p.given else None
    prev_expr = f if t in LIMITS else None
    last_val = None
    for n, raw in lines:
        if SETUP_LINE.match(normalize(raw)) and t != "limit":
            rep.lines.append(LineResult(n, raw, "skipped", "a choice of substitution or parts, not a step to check"))
            continue
        entries = split_entries(raw)
        if not entries:
            rep.lines.append(LineResult(n, raw, "skipped", "nothing to check on this line"))
            continue
        for e in entries:
            try:
                s = parse_answer_expr(e, variables)
            except Exception:  # noqa: BLE001
                rep.lines.append(LineResult(n, e, "skipped", "couldn't read this part (fine if it's notation)"))
                continue
            s = s.subs({sp.Symbol(v): sp.Symbol(v, real=True) for v in variables})
            s = s.xreplace({sp.Symbol("C"): 0, sp.Symbol("C", real=True): 0})
            if s.free_symbols - set(syms):
                rep.lines.append(LineResult(n, e, "skipped", "couldn't read this part (fine if it's notation)"))
                continue
            ok, mistake, why = True, None, ""
            if s.free_symbols & set(syms) or not s.is_number:
                if t in ANTIDERIVATIVE or (t == "definite_integral" and integrand is not None):
                    if "initial" in p.given and t in ANTIDERIVATIVE and not _eq(s, target, syms):
                        if _eq(sp.diff(s, x), integrand, syms):
                            ok, mistake, why = False, "wrong constant from the initial condition", \
                                "The antiderivative is right but the constant doesn't fit the initial condition."
                        else:
                            ok = False
                            mistake, why = classify_antiderivative(s, integrand, x)
                    elif not _eq(sp.diff(s, x), integrand, syms):
                        ok = False
                        mistake, why = classify_antiderivative(s, integrand, x)
                elif t in LIMITS:
                    if prev_expr is not None and not _eq(s, prev_expr, syms):
                        ok = False
                        mistake, why = ("sign error", "This expression is the negative of the one before.") \
                            if _eq(s, -prev_expr, syms) else ("algebra error", "This expression isn't equal to the one before.")
                    else:
                        prev_expr = s
                else:
                    if not _eq(s, target, syms):
                        ok = False
                        if t in ("derivative", "log_differentiation", "higher_derivative") and f is not None:
                            base = f if t != "higher_derivative" else sp.diff(f, x, int(p.given["order"]) - 1)
                            mistake, why = classify_derivative(s, target, base, x)
                        else:
                            mistake, why = "algebra error", "This line isn't equal to the verified answer."
            else:
                if t in NUMBER | LIMITS or not getattr(target, "free_symbols", True):
                    if not _eq(s, target, []):
                        ok = False
                        mistake, why = classify_number(s, target)
                    last_val = s
            if ok:
                rep.lines.append(LineResult(n, e, "ok"))
                last_val = s
            else:
                rep.lines.append(LineResult(n, e, "wrong"))
                rep.first_wrong, rep.mistake, rep.explanation = n, mistake, why
                return
    if last_val is not None:
        if t in ANTIDERIVATIVE:
            rep.final_correct = _eq(sp.diff(last_val, x), integrand, syms) if "initial" not in p.given else \
                _eq(last_val, target, syms)
            if "initial" not in p.given and not re.search(r"\+\s*C\b", raw_text):
                rep.notes.append("Don't forget the + C on an indefinite integral (most markers take a mark off).")
                rep.mistake = rep.mistake or "forgot + C"
        else:
            rep.final_correct = _eq(last_val, target, syms)
        if rep.final_correct is False and rep.first_wrong is None:
            rep.notes.append("Every line is correct so far; the work just isn't finished.")


def _compare_step(sol, mistake: str | None) -> str:
    keys = {"forgot chain rule inner derivative": "chain", "product rule applied wrong": "product",
            "quotient rule order/sign": "quotient", "forgot to divide by the inner derivative": "substitution"}
    k = keys.get(mistake or "")
    if not k:
        return ""
    for i, st in enumerate(sol.steps):
        if k in st.operation.lower():
            return f"Compare with the verified solution, step {i + 1} ({st.operation}): {to_text(st.after)}"
    return ""


def check_attempt(sol, attempt: str) -> CheckReport:
    """``sol`` is the VERIFIED solution of the confirmed problem; ``attempt`` is the student's work."""
    lines = [(i + 1, ln.strip()) for i, ln in enumerate(attempt.splitlines()) if ln.strip()]
    rep = CheckReport()
    t = sol.problem.type
    if t in MATRIX:
        _check_matrices(sol, lines, rep)
    elif t in EQUAL_ANSWER | ANTIDERIVATIVE | LIMITS | NUMBER | {"implicit_derivative"}:
        _check_expressions(sol, lines, rep, attempt)
    else:
        pt = registry.get(t)
        if pt.grade and lines:
            ok, msg = pt.grade(sol, lines[-1][1])
            rep.lines.append(LineResult(lines[-1][0], lines[-1][1], "ok" if ok else "wrong", msg))
            rep.final_correct = ok
            if not ok:
                rep.first_wrong = lines[-1][0]
                rep.mistake = "other"
                rep.explanation = ("For this type GoatVex checks the final answer only. Compare your steps with "
                                   "the write-up.")
    if rep.first_wrong is not None and not sol.problem.is_graded:
        rep.compare_step = _compare_step(sol, rep.mistake)
    if rep.first_wrong is not None:
        rep.final_correct = False
    return rep
