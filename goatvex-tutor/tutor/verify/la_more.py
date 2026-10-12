"""Verifiers for MATH 1104 types beyond RREF/inverse.

Every final answer is recomputed independently (different SymPy algorithms,
NumPy floating point, substitution back into the original conditions).
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from tutor.steps import ROW_OP, Solution
from tutor.text.unicode_math import to_text, vec_text
from tutor.verify.common import equal, ok, verify_steps
from tutor.verify.result import CheckResult


def np_float(m: sp.Matrix) -> np.ndarray:
    return np.array(m.evalf(), dtype=complex if any(not e.is_real for e in m) else float)


def det_two_ways(a: sp.Matrix) -> tuple[sp.Expr, sp.Expr, float]:
    return a.det(method="bareiss"), a.det(method="berkowitz"), complex(np.linalg.det(np_float(a)))


# ---------------------------------------------------------------- determinant
def verify_determinant(solution: Solution) -> list[CheckResult]:
    a = solution.facts["input"]
    out = [ok("s0", "matches the given matrix", solution.problem.matrix == a,
              "A is exactly the confirmed problem", "A differs from problem.json")]
    out += verify_steps(solution)
    if solution.facts["method"] == "row_reduction":
        bareiss = a.det(method="bareiss")
        for s in solution.steps:
            if s.kind == ROW_OP:
                k = s.data["det_sign"]
                out.append(ok(s.id, "det(A) = ±det(current matrix)", k * s.after.det(method="bareiss") == bareiss,
                              f"det(A) = {'−' if k < 0 else ''}det of this matrix (sign tracked correctly)",
                              "the sign bookkeeping is wrong"))
        tri = solution.facts["triangular"]
        out.append(ok("final", "matrix is upper triangular", tri.is_upper, "all entries below the diagonal are 0"))
        last_matrix = [s for s in solution.steps if s.kind == ROW_OP]
        if last_matrix:
            out.append(ok("final", "triangular matrix is the last row-reduced matrix", last_matrix[-1].after == tri,
                          "uses the final matrix of the row reduction"))
    d1, d2, fl = det_two_ways(a)
    v = solution.answer
    out.append(ok("final", "second method: Bareiss + Berkowitz", v == d1 == d2,
                  f"det(A) = {to_text(v)} by two independent algorithms",
                  f"solver {to_text(v)}, Bareiss {to_text(d1)}, Berkowitz {to_text(d2)}"))
    out.append(ok("final", "floating-point cross-check", abs(complex(v) - fl) < 1e-8 * max(1, abs(fl)),
                  f"NumPy gives {fl.real:.6g}"))
    return out


# ---------------------------------------------------------------- Cramer's rule
def verify_cramer(solution: Solution) -> list[CheckResult]:
    A, b = solution.facts["A"], solution.facts["b"]
    out = verify_steps(solution)
    detA = A.det(method="bareiss")
    out.append(equal("final", "det(A) by a second method", solution.facts["detA"], detA))
    if detA == 0:
        out.append(ok("final", "Cramer's rule does not apply", solution.facts.get("applies") is False,
                      "det(A) = 0, so Cramer's rule cannot be used (reported)"))
        return out
    for i, Ai in enumerate(solution.facts["A_i"]):
        expected = A.copy()
        expected[:, i] = b
        out.append(ok("final", f"A{i + 1} built correctly", Ai == expected,
                      f"column {i + 1} of A replaced by b"))
        out.append(equal("final", f"det(A{i + 1}) by a second method", solution.facts["detAi"][i],
                         expected.det(method="berkowitz")))
    x = solution.answer
    out.append(ok("final", "substitute back: A·x = b", A * x == b, "A·x = b exactly", f"A·x = {vec_text(A * x)}"))
    out.append(ok("final", "second method: LU solve", A.LUsolve(b) == x, "LU decomposition gives the same x"))
    return out


# ---------------------------------------------------------------- matrix arithmetic
def verify_matrix_arithmetic(solution: Solution) -> list[CheckResult]:
    from tutor.solvers.linear_algebra.matrix_ops import direct_value, float_value, matrices, parse_matrix_expression

    out = verify_steps(solution)
    mats = matrices(solution.problem)
    expr, _ = parse_matrix_expression(solution.problem.given["expression"], mats)
    direct = direct_value(expr, mats)
    if solution.facts.get("defined", True):
        out.append(equal("final", "second method: direct evaluation", solution.answer, direct)
                   if direct is not None else ok("final", "second method: direct evaluation", False, "", "undefined"))
        try:
            fl = float_value(expr, mats)
            out.append(ok("final", "floating-point cross-check",
                          np.allclose(np.array(solution.answer.evalf(), dtype=float), fl), "NumPy agrees"))
        except Exception as exc:
            out.append(ok("final", "floating-point cross-check", False, "", f"NumPy failed: {exc}"))
    else:
        out.append(ok("final", "undefined operation confirmed", direct is None,
                      solution.facts.get("why_undefined", "sizes don't match")))
    return out


# ---------------------------------------------------------------- complex numbers
def _mp(z):
    import mpmath

    with mpmath.workdps(40):
        return mpmath.mpc(complex(sp.N(z, 45)))


def _close(a, b, tol=1e-12) -> bool:
    za, zb = complex(sp.N(a, 30)), complex(sp.N(b, 30))
    return abs(za - zb) <= tol * max(1.0, abs(zb))


def verify_complex(solution: Solution) -> list[CheckResult]:
    from tutor.parse.schema import parse_math
    from tutor.solvers.linear_algebra.complex_numbers import parts

    p = solution.problem
    task = solution.facts["task"]
    out = verify_steps(solution)
    I = sp.I
    if task == "simplify":
        direct = sp.expand_complex(sp.simplify(parse_math(p.given["expression"], imaginary=True)))
        out.append(equal("final", "second method: SymPy evaluates the whole expression", solution.answer, direct))
        out.append(ok("final", "floating-point cross-check", _close(solution.answer, direct), "complex floats agree"))
        a, b = parts(solution.answer)
        out.append(ok("final", "answer is in a + bi form", (a.is_real and b.is_real) and not a.has(I) and not b.has(I),
                      f"a = {to_text(a)}, b = {to_text(b)}"))
        return out
    if task in ("polar", "power", "roots"):
        z = solution.facts.get("z", solution.facts.get("w"))
        given = parse_math(p.given["z" if "z" in p.given else "w"], imaginary=True)
        out.append(equal("s0", "uses the given number", z, given))
        r, th = solution.facts["r"], solution.facts["theta"]
        a, b = parts(z)
        out.append(equal("final", "r = |z|", r, sp.Abs(given)))
        out.append(equal("final", "cos θ = a/r", sp.cos(th), a / r))
        out.append(equal("final", "sin θ = b/r", sp.sin(th), b / r))
        out.append(ok("final", "θ is the principal argument (−π < θ ≤ π)", bool(-sp.pi < th) and bool(th <= sp.pi),
                      f"θ = {to_text(th)}"))
        out.append(equal("final", "r(cos θ + i sin θ) gives back z", sp.expand_complex(r * (sp.cos(th) + I * sp.sin(th))), z))
    if task == "power":
        n = solution.facts["n"]
        direct = sp.expand_complex(sp.expand(z ** n))
        out.append(equal("final", "second method: multiply out zⁿ directly", solution.answer, direct))
        out.append(ok("final", "floating-point cross-check", _close(solution.answer, complex(sp.N(z)) ** n), "agrees"))
    if task == "roots":
        n = solution.facts["n"]
        roots = solution.answer
        out.append(ok("final", f"exactly {n} roots", len(roots) == n, f"{len(roots)} roots listed"))
        for k, zk in enumerate(roots):
            out.append(equal("final", f"root {k}: z^{n} = w", sp.expand_complex(sp.expand(zk ** n)), z))
        distinct = all(not _close(roots[i], roots[j]) for i in range(n) for j in range(i + 1, n))
        out.append(ok("final", "roots are all different", distinct, "no repeated roots"))
        zs = sp.Symbol("zz")
        poly_roots = sp.Poly(zs ** n - z, zs).nroots(n=30)
        matched = all(any(_close(r_, pr) for pr in poly_roots) for r_ in roots)
        out.append(ok("final", "second method: numeric roots of zⁿ − w", matched, "every root matches a numeric root"))
    if task == "quadratic":
        a, b, c = (solution.facts[k] for k in ("a", "b", "c"))
        zs = sp.Symbol("zz")
        for k, root in enumerate(solution.answer, 1):
            out.append(equal("final", f"root {k} satisfies the equation", sp.expand(a * root ** 2 + b * root + c), 0))
        sym = sp.solve(a * zs ** 2 + b * zs + c, zs)
        matched = all(any(_close(r_, s_) for s_ in sym) for r_ in solution.answer) and len(set(sym)) <= 2
        out.append(ok("final", "second method: SymPy solve", matched, "same roots"))
    return out


# ---------------------------------------------------------------- vectors, lines, planes
def verify_geometry(solution: Solution) -> list[CheckResult]:
    from tutor.solvers.linear_algebra.geometry import T, XYZ, read_line, read_plane

    p = solution.problem
    task = solution.facts["task"]
    out = verify_steps(solution)
    ans = solution.answer
    vec = lambda k: sp.Matrix(p.vec(k))  # noqa: E731

    def on_plane(pt, n, c):
        return sp.simplify((n.T * sp.Matrix(pt))[0] - c) == 0

    def eq_holds(eqs, point):
        subs = {XYZ[i]: point[i] for i in range(len(point))}
        return all(sp.simplify(e.lhs.subs(subs) - e.rhs.subs(subs)) == 0 for e in eqs)

    def line_at(eqs, tval):
        return [sp.simplify(e.rhs.subs(T, tval)) for e in eqs]

    if task == "dot":
        u, v = vec("u"), vec("v")
        out.append(equal("final", "second method: SymPy dot", ans, u.dot(v)))
        out.append(ok("final", "floating-point cross-check",
                      abs(float(ans) - float(np.dot(np_float(u).ravel(), np_float(v).ravel()))) < 1e-9, "NumPy agrees"))
    elif task == "norm":
        u = vec("u")
        out.append(equal("final", "second method: SymPy norm", ans, u.norm()))
        out.append(ok("final", "floating-point cross-check",
                      abs(float(ans) - float(np.linalg.norm(np_float(u)))) < 1e-9, "NumPy agrees"))
    elif task == "unit":
        u = vec("u")
        out.append(equal("final", "answer has length 1", sp.Matrix(ans).norm(), 1))
        out.append(ok("final", "same direction as u", sp.simplify(sp.Matrix(ans) * u.norm() - u) == sp.zeros(u.rows, 1),
                      "‖u‖·answer = u"))
    elif task == "angle":
        u, v = vec("u"), vec("v")
        out.append(equal("final", "cos θ · ‖u‖‖v‖ = u·v", sp.cos(ans) * u.norm() * v.norm(), u.dot(v)))
        out.append(ok("final", "0 ≤ θ ≤ π", bool(0 <= ans) and bool(ans <= sp.pi), f"θ = {to_text(ans)}"))
        fl = float(np.arccos(np.dot(np_float(u).ravel(), np_float(v).ravel()) /
                             (np.linalg.norm(np_float(u)) * np.linalg.norm(np_float(v)))))
        out.append(ok("final", "floating-point cross-check", abs(float(ans) - fl) < 1e-9, f"NumPy gives {fl:.6f} rad"))
    elif task == "projection":
        u, v = vec("u"), vec("v")
        proj = sp.Matrix(ans)
        out.append(ok("final", "u − proj is orthogonal to v", sp.simplify((u - proj).dot(v)) == 0, "(u − proj)·v = 0"))
        out.append(ok("final", "proj is a multiple of v", sp.Matrix.hstack(proj, v).rank() <= 1, "proj ∥ v"))
        out.append(equal("final", "second method: SymPy project", proj, u.project(v)))
    elif task == "cross":
        u, v = vec("u"), vec("v")
        c = sp.Matrix(ans)
        out.append(ok("final", "u × v is orthogonal to u", c.dot(u) == 0, "(u × v)·u = 0"))
        out.append(ok("final", "u × v is orthogonal to v", c.dot(v) == 0, "(u × v)·v = 0"))
        out.append(equal("final", "Lagrange identity ‖u×v‖² = ‖u‖²‖v‖² − (u·v)²", c.dot(c),
                         u.dot(u) * v.dot(v) - u.dot(v) ** 2))
        out.append(equal("final", "second method: SymPy cross", c, u.cross(v)))
    elif task in ("area_parallelogram", "area_triangle"):
        u, v = vec("u"), vec("v")
        area = sp.sqrt(u.dot(u) * v.dot(v) - u.dot(v) ** 2)  # no cross product involved
        if task == "area_triangle":
            area = area / 2
        out.append(equal("final", "second method: √(‖u‖²‖v‖² − (u·v)²)", ans, area))
    elif task == "line_through_points":
        P, Q, eqs = vec("P"), vec("Q"), ans
        out.append(ok("final", "t = 0 gives P", line_at(eqs, 0) == list(P), "the line passes through P"))
        out.append(ok("final", "t = 1 gives Q", line_at(eqs, 1) == list(Q), "the line passes through Q"))
    elif task == "plane_point_normal":
        P, n = vec("P"), vec("n")
        out.append(ok("final", "P is on the plane", eq_holds([ans], P), "substituting P satisfies the equation"))
        coeffs = [ans.lhs.coeff(v_) for v_ in XYZ[:n.rows]]
        out.append(ok("final", "normal vector matches", coeffs == list(n), f"coefficients {vec_text(coeffs)} = n"))
    elif task == "plane_through_points":
        for k in ("P", "Q", "R"):
            out.append(ok("final", f"{k} is on the plane", eq_holds([ans], vec(k)), f"{k} satisfies the equation"))
        coeffs = sp.Matrix([ans.lhs.coeff(v_) for v_ in XYZ])
        out.append(ok("final", "it is a plane (normal ≠ 0)", coeffs != sp.zeros(3, 1), "nonzero normal"))
    elif task == "line_plane_intersection":
        P, d = read_line(p, "line")
        n, c = read_plane(p, "plane")
        nd = (n.T * d)[0]
        if isinstance(ans, str):
            out.append(ok("final", "line is parallel to the plane", nd == 0, "n·d = 0"))
            out.append(ok("final", "P on plane?", (ans == "line_in_plane") == on_plane(P, n, c),
                          "correctly decided whether the line lies in the plane"))
        else:
            out.append(ok("final", "point is on the plane", on_plane(ans, n, c), "satisfies the plane equation"))
            tt = sp.solve(sp.Matrix(ans) - (sp.Matrix(P) + T * sp.Matrix(d)), T, dict=True)
            out.append(ok("final", "point is on the line", bool(tt), "it equals P + t·d for one t"))
    elif task == "line_line_intersection":
        P1, d1 = read_line(p, "line1")
        P2, d2 = read_line(p, "line2")
        S_ = sp.Symbol("s_", real=True)
        sys_ = list(sp.Matrix(P1) + T * sp.Matrix(d1) - sp.Matrix(P2) - S_ * sp.Matrix(d2))
        indep = sp.solve(sys_, [T, S_], dict=True)
        if isinstance(ans, str):
            if ans == "same_line":
                out.append(ok("final", "infinitely many solutions", bool(indep) and (T not in indep[0] or S_ not in indep[0]),
                              "the lines coincide"))
            else:
                out.append(ok("final", "no common point", not indep, "the equations are inconsistent"))
                par = sp.Matrix.hstack(sp.Matrix(d1), sp.Matrix(d2)).rank() == 1
                out.append(ok("final", "parallel vs skew decided correctly", (ans == "parallel") == par,
                              "direction vectors " + ("are" if par else "are not") + " parallel"))
        else:
            for k, (Pk, dk) in enumerate(((P1, d1), (P2, d2)), 1):
                tt = sp.solve(sp.Matrix(ans) - (sp.Matrix(Pk) + T * sp.Matrix(dk)), T, dict=True)
                out.append(ok("final", f"point is on line {k}", bool(tt), f"it lies on line {k}"))
    elif task == "plane_plane_intersection":
        n1, c1 = read_plane(p, "plane1")
        n2, c2 = read_plane(p, "plane2")
        if isinstance(ans, str):
            out.append(ok("final", "normals are parallel", sp.Matrix(n1).cross(sp.Matrix(n2)) == sp.zeros(3, 1), "n₁ × n₂ = 0"))
            same = sp.Matrix([[*n1, c1], [*n2, c2]]).rank() == 1
            out.append(ok("final", "same vs parallel decided correctly", (ans == "same_plane") == same, "checked by rank"))
        else:
            pt = [e.rhs for e in ans]
            out.append(ok("final", "the whole line lies in plane 1", sp.expand((n1.T * sp.Matrix(pt))[0] - c1) == 0,
                          "n₁·(point + t·d) = c₁ for every t"))
            out.append(ok("final", "the whole line lies in plane 2", sp.expand((n2.T * sp.Matrix(pt))[0] - c2) == 0,
                          "n₂·(point + t·d) = c₂ for every t"))
            dvec = sp.Matrix([sp.diff(x_, T) for x_ in pt])
            out.append(ok("final", "direction is nonzero", dvec != sp.zeros(3, 1), "a genuine line"))
    elif task == "point_plane_distance":
        Q = vec("Q")
        n, c = read_plane(p, "plane")
        n = sp.Matrix(n)
        F = Q - ((n.dot(Q) - c) / n.dot(n)) * n  # foot of the perpendicular (independent route)
        out.append(ok("final", "foot of perpendicular is on the plane", on_plane(F, n, c), "F on the plane"))
        out.append(equal("final", "second method: ‖Q − F‖", ans, (Q - F).norm()))
    elif task == "point_line_distance":
        Q = vec("Q")
        P, d = read_line(p, "line")
        P, d = sp.Matrix(P), sp.Matrix(d)
        F = sp.Matrix(solution.facts["F"])
        out.append(ok("final", "QF is perpendicular to the line", sp.simplify((Q - F).dot(d)) == 0, "(Q − F)·d = 0"))
        if P.rows == 3:
            alt = (Q - P).cross(d).norm() / d.norm()
            out.append(equal("final", "second method: ‖PQ × d‖/‖d‖", ans, alt))
        else:
            alt = sp.Abs((Q - P)[0] * d[1] - (Q - P)[1] * d[0]) / d.norm()
            out.append(equal("final", "second method: |det(PQ, d)|/‖d‖", ans, alt))
    return out


# ---------------------------------------------------------------- span / independence / bases
def verify_subspaces(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    task = f["task"]
    out = verify_steps(solution)
    if task == "span":
        vs, w = f["vectors"], f["w"]
        V_ = sp.Matrix.hstack(*vs)
        r1, r2 = V_.rank(), sp.Matrix.hstack(V_, w).rank()
        if solution.answer:
            c = f["coefficients"]
            out.append(ok("final", "the combination really gives w", V_ * c == w, "Σ cᵢvᵢ = w exactly"))
        out.append(ok("final", "second method: rank test", (r1 == r2) == bool(solution.answer),
                      f"rank[v₁…vₖ] = {r1}, rank[v₁…vₖ | w] = {r2}"))
    elif task == "independence":
        m = f["matrix"]
        k = m.cols
        if solution.answer:
            out.append(ok("final", "second method: rank = number of vectors", m.rank() == k == np.linalg.matrix_rank(np_float(m)),
                          f"rank = {k} (SymPy and NumPy)"))
        else:
            rel = f["relation"]
            out.append(ok("final", "dependence relation is nonzero", rel != sp.zeros(k, 1), "not all cᵢ are 0"))
            out.append(ok("final", "dependence relation gives 0", m * rel == sp.zeros(m.rows, 1), "Σ cᵢvᵢ = 0 exactly"))
            out.append(ok("final", "second method: rank < number of vectors", m.rank() < k, f"rank = {m.rank()} < {k}"))
    else:
        a = f["matrix"]
        rank, nul = f["rank"], f["null_basis"]
        out.append(ok("final", "rank by two methods", rank == a.rank() == np.linalg.matrix_rank(np_float(a)),
                      f"rank = {rank} (pivots = SymPy = NumPy SVD)"))
        for k, v in enumerate(nul, 1):
            out.append(ok("final", f"null vector {k}: A·v = 0", a * v == sp.zeros(a.rows, 1), "A·v = 0 exactly"))
        if nul:
            out.append(ok("final", "null basis is independent", sp.Matrix.hstack(*nul).rank() == len(nul), "full rank"))
        out.append(ok("final", "rank–nullity", rank + len(nul) == a.cols, f"{rank} + {len(nul)} = {a.cols}"))
        out.append(ok("final", "nullity matches SymPy nullspace", len(nul) == len(a.nullspace()),
                      f"dim Nul(A) = {len(nul)}"))
        cb = sp.Matrix.hstack(*f["col_basis"]) if f["col_basis"] else sp.zeros(a.rows, 0)
        out.append(ok("final", "column basis: independent and spans Col(A)",
                      cb.rank() == len(f["col_basis"]) == rank and sp.Matrix.hstack(cb, a).rank() == rank,
                      "rank of the basis = rank of [basis | A] = rank(A)"))
        rb = sp.Matrix.hstack(*f["row_basis"]).T if f["row_basis"] else sp.zeros(0, a.cols)
        out.append(ok("final", "row basis: independent and spans Row(A)",
                      rb.rank() == rank and sp.Matrix.vstack(rb, a).rank() == rank, "same rank when stacked with A"))
    return out


# ---------------------------------------------------------------- eigenvalues / diagonalization
def verify_eigen(solution: Solution) -> list[CheckResult]:
    from tutor.solvers.linear_algebra.eigen import LAM

    f = solution.facts
    a = f["matrix"]
    n = a.rows
    out = verify_steps(solution, [LAM])
    for s in solution.steps:
        if s.data.get("rule") == "shift":
            out.append(ok(s.id, "A − λI formed correctly", s.after == a - LAM * sp.eye(n), "diagonal shifted by λ"))
    # SymPy's charpoly is det(λI − A) = (−1)ⁿ det(A − λI)
    out.append(equal("final", "second method: SymPy charpoly", f["charpoly"], (-1) ** n * a.charpoly(LAM).as_expr(),
                     [LAM]))
    total = sum(f["multiplicities"].values())
    out.append(ok("final", "multiplicities add to n", total == n, f"{total} = {n}"))
    for lv in f["eigenvalues"]:
        out.append(equal("final", f"λ = {to_text(lv)} is a root", f["charpoly"].subs(LAM, lv), 0))
        basis = f["spaces"][lv]
        for k, v in enumerate(basis, 1):
            out.append(ok("final", f"λ = {to_text(lv)}: eigenvector {k} is nonzero", v != sp.zeros(n, 1), "v ≠ 0"))
            resid = (a * v - lv * v).applyfunc(sp.simplify)
            out.append(ok("final", f"λ = {to_text(lv)}: A·v = λ·v", resid == sp.zeros(n, 1), "A·v − λ·v = 0 exactly"))
        geo = n - (a - lv * sp.eye(n)).rank(simplify=True)
        out.append(ok("final", f"λ = {to_text(lv)}: eigenspace dimension", geo == len(basis),
                      f"dim = n − rank(A − λI) = {geo}"))
    fl = np.sort_complex(np.linalg.eigvals(np_float(a)))
    mine = np.sort_complex(np.array([complex(sp.N(lv)) for lv in f["eigenvalues"] for _ in range(f["multiplicities"][lv])]))
    out.append(ok("final", "floating-point cross-check (NumPy eigvals)", np.allclose(fl, mine, atol=1e-6),
                  "NumPy finds the same eigenvalues"))
    if f["task"] == "diagonalize":
        if f.get("diagonalizable"):
            P, Dm, Pinv = f["P"], f["D"], f["Pinv"]
            out.append(ok("final", "P·P⁻¹ = I", (P * Pinv).applyfunc(sp.simplify) == sp.eye(n), "exactly"))
            out.append(ok("final", "P·D·P⁻¹ = A", (P * Dm * Pinv).applyfunc(sp.simplify) == a, "exactly"))
            out.append(ok("final", "det(P) ≠ 0", sp.simplify(P.det()) != 0, "P is invertible"))
        else:
            out.append(ok("final", "second method: SymPy is_diagonalizable", not a.is_diagonalizable(),
                          "SymPy agrees it is not diagonalizable"))
    return out


# ---------------------------------------------------------------- linear transformations / orthogonality
def verify_transformation(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    xs, comps = f["xs"], f["comps"]
    out = verify_steps(solution, xs)
    if not f["linear"]:
        T2, T1 = f["T2"], f["T1"]
        out.append(ok("final", "counterexample is real", list(T2) != [2 * v for v in T1], "T(2e₁) ≠ 2T(e₁)"))
        return out
    A_ = f["A"]
    X = sp.Matrix(xs)
    out.append(ok("final", "A·x reproduces the formula", (A_ * X - sp.Matrix(comps)).applyfunc(sp.expand) ==
                  sp.zeros(len(comps), 1), "A·x = T(x) for every x"))
    if "v" in f:
        out.append(ok("final", "T(v) by substitution", sp.Matrix(f["Tv"]) == sp.Matrix([c.subs(dict(zip(xs, f["v"])))
                                                                                       for c in comps]),
                      "plugging v into the formula gives the same vector"))
    if "kernel" in f:
        for k, v in enumerate(f["kernel"], 1):
            out.append(ok("final", f"kernel vector {k} maps to 0", A_ * v == sp.zeros(A_.rows, 1), "A·v = 0"))
        out.append(ok("final", "dim ker + dim range = n", len(f["kernel"]) + len(f["range"]) == A_.cols,
                      "rank–nullity"))
        out.append(ok("final", "second method: rank", len(f["range"]) == A_.rank(), f"rank = {A_.rank()}"))
    return out


def verify_orthogonal(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    out = verify_steps(solution)
    vs = [sp.Matrix(v) for v in (solution.answer if f["task"] == "gram_schmidt" else f["vs"])]
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            out.append(ok("final", f"v{i + 1} ⟂ v{j + 1}", (vs[i].T * vs[j])[0] == 0, "dot product 0"))
    base = f["xs"] if f["task"] == "gram_schmidt" else f["us"]
    X = sp.Matrix.hstack(*[sp.Matrix(x) for x in base])
    Vm = sp.Matrix.hstack(*vs)
    out.append(ok("final", "same span as the original vectors", Vm.rank() == X.rank() == sp.Matrix.hstack(Vm, X).rank(),
                  "rank[V] = rank[X] = rank[V | X]"))
    if f["task"] == "gram_schmidt":
        for k in range(1, len(vs) + 1):  # Gram–Schmidt keeps span{v₁…vₖ} = span{x₁…xₖ} for every k
            out.append(ok("final", f"span of the first {k} is preserved",
                          sp.Matrix.hstack(*vs[:k], *[sp.Matrix(x) for x in base[:k]]).rank() == k, "nested spans"))
        if f["normalize"]:
            for i, v in enumerate(vs, 1):
                out.append(equal("final", f"‖q{i}‖ = 1", sp.sqrt((v.T * v)[0]), 1))
    else:
        y, proj, perp = sp.Matrix(f["y"]), sp.Matrix(f["proj"]), sp.Matrix(f["perp"])
        for k, u in enumerate(f["us"], 1):
            out.append(ok("final", f"y − proj ⟂ u{k}", sp.simplify((perp.T * sp.Matrix(u))[0]) == 0, "orthogonal"))
        out.append(ok("final", "proj lies in W", sp.Matrix.hstack(X, proj).rank() == X.rank(), "in the span"))
        normal = X * (X.T * X).inv() * X.T * y  # normal equations: an independent formula for the projection
        out.append(equal("final", "second method: X(XᵀX)⁻¹Xᵀy", proj, sp.ImmutableMatrix(normal)))
    return out
