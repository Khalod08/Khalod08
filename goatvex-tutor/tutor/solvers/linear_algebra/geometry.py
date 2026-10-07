"""Vectors, lines and planes in ℝ² and ℝ³ (Nicholson 4.1–4.2, Poole 1.1–1.3).

Vector tasks: dot, norm, unit, angle, projection, cross, area.
Line/plane tasks: line_through_points, plane_through_points, plane_point_normal,
line_plane_intersection, line_line_intersection, plane_plane_intersection,
point_plane_distance, point_line_distance.

Every computation shows its formula with the numbers in place before the
result. Special cases (parallel, skew, collinear) are detected and reported.
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem
from tutor.solvers.builder import A, Builder, M, dot_formula, frac, sumsq_formula
from tutor.steps import FACT, Solution
from tutor.text.unicode_math import to_text, vec_text

X, Y, Z = sp.symbols("x y z", real=True)
T, S = sp.symbols("t s", real=True)
XYZ = (X, Y, Z)


def V(entries) -> sp.ImmutableMatrix:
    return sp.ImmutableMatrix(entries)


def vt(v) -> str:
    return vec_text(v)


# ------------------------------------------------------------------ building blocks
def dot(B: Builder, u, v, label="u·v") -> sp.Expr:
    return B.add(dot_formula(list(u), list(v)), f"{label} = u₁v₁ + u₂v₂ + …", (V(u).T * V(v))[0],
                 "Multiply matching components and add.")


def norm(B: Builder, u, label="‖u‖") -> sp.Expr:
    formula = sp.sqrt(sumsq_formula(list(u)), evaluate=False)
    return B.add(formula, f"{label} = √(sum of squares)", sp.sqrt(sum(c**2 for c in u)),
                 "Square each component, add, take the square root.")


def cross(B: Builder, u, v, label="u × v") -> sp.ImmutableMatrix:
    if len(u) != 3:
        raise ProblemFormatError("the cross product needs vectors in ℝ³")
    u1, u2, u3 = u
    v1, v2, v3 = v
    formula = V([A(M(u2, v3), M(-1, M(u3, v2))), A(M(u3, v1), M(-1, M(u1, v3))), A(M(u1, v2), M(-1, M(u2, v1)))])
    return B.add(formula, f"{label} = (u₂v₃ − u₃v₂, u₃v₁ − u₁v₃, u₁v₂ − u₂v₁)", V(sp.Matrix(u).cross(sp.Matrix(v))),
                 "Each component is a 2×2 determinant of the other two components.")


def plane_eq(n, d):
    return sp.Eq(n[0] * X + n[1] * Y + (n[2] * Z if len(n) > 2 else 0), d)


def line_point(P, d, t):
    return V([P[i] + t * d[i] for i in range(len(P))])


def point_formula(P, t, d):
    """P + t·d with the numbers in place, component by component."""
    return V([A(P[i], M(t, d[i])) for i in range(len(P))])


def parametric(P, d, t=T):
    names = XYZ[:len(P)]
    return [sp.Eq(names[i], P[i] + d[i] * t) for i in range(len(P))]


def read_plane(p: Problem, key: str):
    """A plane given as "2x - y + 3z = 4" → (normal, d)."""
    from tutor.parse.schema import parse_math

    text = p.given[key]
    if "=" not in text:
        raise ProblemFormatError(f"{key}: write the plane as an equation like 2x - y + 3z = 4")
    lhs, rhs = text.split("=", 1)
    e = parse_math(lhs, ["x", "y", "z"]) - parse_math(rhs, ["x", "y", "z"])
    poly = sp.Poly(e, X, Y, Z)
    if poly.total_degree() != 1:
        raise ProblemFormatError(f"{key} is not a plane (it must be linear in x, y, z)")
    n = V([poly.coeff_monomial(X), poly.coeff_monomial(Y), poly.coeff_monomial(Z)])
    d = -poly.coeff_monomial(1)
    if n == V([0, 0, 0]):
        raise ProblemFormatError(f"{key} has no x, y or z term")
    return n, d


def read_line(p: Problem, key: str):
    """A line given as {"point": [...], "direction": [...]}."""
    ln = p.given[key]
    if not isinstance(ln, dict) or "point" not in ln or "direction" not in ln:
        raise ProblemFormatError(f"{key} must be {{\"point\": [...], \"direction\": [...]}}")
    from tutor.parse.schema import parse_vector

    P, d = V(parse_vector(ln["point"])), V(parse_vector(ln["direction"]))
    if d == sp.zeros(d.rows, 1):
        raise ProblemFormatError(f"{key}: the direction vector cannot be 0")
    if P.rows != d.rows:
        raise ProblemFormatError(f"{key}: point and direction must have the same number of components")
    return P, d


# ------------------------------------------------------------------ tasks
def solve(p: Problem) -> Solution:
    task = p.given["task"]
    B = Builder()
    facts: dict = {"task": task}
    notes: list[str] = []
    g = p.given
    vec = lambda k: V(p.vec(k))  # noqa: E731

    if task == "dot":
        u, v = vec("u"), vec("v")
        answer, label = dot(B, u, v), "u·v"
        if answer == 0:
            notes.append("u·v = 0, so u and v are orthogonal.")
    elif task == "norm":
        u = vec("u")
        answer, label = norm(B, u), "‖u‖"
    elif task == "unit":
        u = vec("u")
        n = norm(B, u)
        if n == 0:
            raise UnsupportedProblem("the zero vector has no unit vector")
        answer = B.add(M(frac(1, n), u), "u/‖u‖", V(u / n), "Divide every component by the length.")
        label = "unit vector"
    elif task == "angle":
        u, v = vec("u"), vec("v")
        d = dot(B, u, v)
        nu = norm(B, u, "‖u‖")
        nv = norm(B, v, "‖v‖")
        if nu == 0 or nv == 0:
            raise UnsupportedProblem("the angle with the zero vector is undefined")
        c = B.add(frac(d, M(nu, nv)), "cos θ = u·v / (‖u‖‖v‖)", sp.nsimplify(sp.radsimp(d / (nu * nv))),
                  "Divide the dot product by the product of the lengths.")
        theta = sp.acos(c)
        answer = B.add(sp.acos(c, evaluate=False), "θ = arccos(cos θ)", theta,
                       f"θ is between 0 and π. In degrees: ≈ {float(sp.deg(theta)):.2f}°.")
        label = "θ"
        facts.update(u=u, v=v)
    elif task == "projection":
        u, v = vec("u"), vec("v")
        d = dot(B, u, v)
        nv2 = B.add(sumsq_formula(list(v)), "‖v‖² = v·v", sum(c**2 for c in v), "Sum of the squares of v.")
        if nv2 == 0:
            raise UnsupportedProblem("you can't project onto the zero vector")
        k = B.add(frac(d, nv2), "scalar (u·v)/‖v‖²", d / nv2, "Divide.")
        proj = B.add(M(k, v), "proj_v u = ((u·v)/‖v‖²) v", V(k * v), "Multiply v by the scalar.")
        perp = B.add(A(u, M(-1, proj)), "u − proj_v u (the part of u orthogonal to v)", V(u - proj),
                     "Subtract component by component.")
        answer, label = proj, "proj_v u"
        notes.append(f"Orthogonal part: u − proj_v u = {vt(perp)}.")
        facts.update(u=u, v=v, perp=perp)
    elif task == "cross":
        u, v = vec("u"), vec("v")
        answer, label = cross(B, u, v), "u × v"
    elif task in ("area_parallelogram", "area_triangle"):
        u, v = vec("u"), vec("v")
        c = cross(B, u, v)
        n = norm(B, c, "‖u × v‖")
        if task == "area_triangle":
            answer = B.add(frac(n, 2), "Area = ½‖u × v‖", n / 2, "A triangle is half the parallelogram.")
        else:
            answer = n
        label = "area"
    elif task == "line_through_points":
        P, Q = vec("P"), vec("Q")
        d = B.add(A(Q, M(-1, P)), "Direction d = Q − P", V(Q - P), "Subtract the coordinates of P from Q.")
        if d == sp.zeros(P.rows, 1):
            raise UnsupportedProblem("P and Q are the same point, so they don't determine a line")
        eqs = parametric(P, d)
        B.add(None, "Vector and parametric equations", eqs,
              f"x = P + t·d = {vt(P)} + t{vt(d)}, t ∈ ℝ.", kind=FACT)
        answer, label = eqs, "the line"
        facts.update(P=P, Q=Q, d=d)
    elif task == "plane_point_normal":
        P, n = vec("P"), vec("n")
        d = dot(B, n, P, "n·P")
        eq = plane_eq(n, d)
        answer = B.add(None, "n·(x, y, z) = n·P", eq, "A point (x, y, z) is on the plane exactly when x − P ⟂ n.",
                       kind=FACT)
        label = "plane"
        facts.update(P=P, n=n)
    elif task == "plane_through_points":
        P, Q, R = vec("P"), vec("Q"), vec("R")
        u = B.add(A(Q, M(-1, P)), "u = Q − P", V(Q - P), "Two vectors lying in the plane…")
        v = B.add(A(R, M(-1, P)), "v = R − P", V(R - P), "…from P to the other two points.")
        n = cross(B, u, v, "n = u × v")
        if n == V([0, 0, 0]):
            raise UnsupportedProblem("the three points are on one line (u × v = 0), so they don't determine a unique plane")
        d = dot(B, n, P, "n·P")
        eq = plane_eq(n, d)
        answer = B.add(None, "Plane: n·(x, y, z) = n·P", eq, "n is perpendicular to the plane.", kind=FACT)
        label = "plane"
        facts.update(P=P, Q=Q, R=R, n=n)
    elif task == "line_plane_intersection":
        P, d = read_line(p, "line")
        n, c = read_plane(p, "plane")
        sub_eq = sp.Eq((n.T * line_point(P, d, T))[0], c)
        B.add(None, "Substitute the line into the plane", sub_eq,
              "Points on the line are P + t·d; put x, y, z into the plane's equation.", kind=FACT)
        nd = (n.T * d)[0]
        if nd == 0:
            on = (n.T * P)[0] == c
            answer = "line_in_plane" if on else "no_intersection"
            notes.append("n·d = 0, so the line is parallel to the plane. "
                         + ("P is on the plane, so the whole line lies in it." if on else "P is not on the plane: no intersection."))
            label = "intersection"
        else:
            tval = sp.solve(sub_eq, T)[0]
            B.add(sub_eq, "Solve for t", sp.Eq(T, tval), "A linear equation in t.", kind="equation", unknowns=[T],
                  chain=False)
            answer = B.add(point_formula(P, tval, d), "Put t back into the line", V(P + tval * d),
                           f"t = {to_text(tval)}.")
            label = "intersection point"
        facts.update(P=P, d=d, n=n, c=c)
    elif task == "line_line_intersection":
        P1, d1 = read_line(p, "line1")
        P2, d2 = read_line(p, "line2")
        eqs = [sp.Eq(P1[i] + T * d1[i], P2[i] + S * d2[i]) for i in range(P1.rows)]
        B.add(None, "Set the lines equal", eqs, "P₁ + t·d₁ = P₂ + s·d₂, one equation per coordinate.", kind=FACT)
        sol = sp.solve(eqs, [T, S], dict=True)
        parallel = sp.Matrix(d1).cross(sp.Matrix(d2)) == sp.zeros(3, 1) if P1.rows == 3 else d1[0] * d2[1] - d1[1] * d2[0] == 0
        if sol:
            tval, sval = sol[0].get(T, 0), sol[0].get(S, 0)
            if T not in sol[0] or S not in sol[0]:
                answer, label = "same_line", "intersection"
                notes.append("The equations hold for infinitely many t, s: the lines are the same line.")
            else:
                B.add(eqs, "Solve for t and s", [sp.Eq(T, tval), sp.Eq(S, sval)], "Solve two equations, check the rest.",
                      kind="equation", unknowns=[T, S])
                answer = B.add(point_formula(P1, tval, d1), "Intersection point", V(P1 + tval * d1),
                               f"Put t = {to_text(tval)} into line 1.")
                label = "intersection point"
        else:
            answer = "parallel" if parallel else "skew"
            label = "intersection"
            notes.append("No t, s satisfy all equations. " + ("The direction vectors are parallel, so the lines are "
                                                              "parallel (distinct)." if parallel else
                                                              "The directions are not parallel, so the lines are skew."))
        facts.update(P1=P1, d1=d1, P2=P2, d2=d2, parallel=parallel)
    elif task == "plane_plane_intersection":
        n1, c1 = read_plane(p, "plane1")
        n2, c2 = read_plane(p, "plane2")
        dvec = cross(B, n1, n2, "d = n₁ × n₂")
        if dvec == V([0, 0, 0]):
            same = sp.Matrix([*n1, c1]).rank() == sp.Matrix([[*n1, c1], [*n2, c2]]).rank()
            answer = "same_plane" if same else "parallel"
            label = "intersection"
            notes.append("n₁ × n₂ = 0: the planes are parallel" + (" and identical." if same else ", with no intersection."))
        else:
            # a point: set one coordinate to 0 (any whose d-component is nonzero), preferring whole numbers
            choices = []
            for k in sorted(range(3), key=lambda i: -abs(dvec[i])):
                if dvec[k] == 0:
                    continue
                zv = XYZ[k]
                rest = [v for v in XYZ if v != zv]
                e2 = [plane_eq(n1, c1).subs(zv, 0), plane_eq(n2, c2).subs(zv, 0)]
                sl = sp.solve(e2, rest, dict=True)[0]
                choices.append((not all(val.is_Integer for val in sl.values()), k, zv, rest, e2, sl))
            _, k, zero_var, others, eqs, sol = min(choices, key=lambda c: (c[0], c[1]))
            point = V([sol.get(v, 0) if v != zero_var else 0 for v in XYZ])
            B.add(eqs, f"Find a point: set {zero_var} = 0", [sp.Eq(v, sol[v]) for v in others],
                  "Any point on both planes works; with one coordinate 0 the two equations have one solution.",
                  kind="equation", unknowns=others)
            answer = parametric(point, dvec)
            B.add(None, "Line of intersection", answer, f"x = {vt(point)} + t{vt(dvec)}, t ∈ ℝ.", kind=FACT)
            label = "line of intersection"
            facts.update(point=point, d=dvec)
        facts.update(n1=n1, c1=c1, n2=n2, c2=c2)
    elif task == "point_plane_distance":
        Q = vec("Q")
        n, c = read_plane(p, "plane")
        nq = dot(B, n, Q, "n·Q")
        nn = norm(B, n, "‖n‖")
        answer = B.add(frac(sp.Abs(A(nq, -c), evaluate=False), nn), "distance = |n·Q − d| / ‖n‖",
                       sp.radsimp(sp.Abs(nq - c) / nn), "The formula for the distance from a point to a plane.")
        label = "distance"
        facts.update(Q=Q, n=n, c=c)
    elif task == "point_line_distance":
        Q = vec("Q")
        P, d = read_line(p, "line")
        PQ = B.add(A(Q, M(-1, P)), "PQ = Q − P", V(Q - P), "Vector from the line's point to Q.")
        k = B.add(frac(dot_formula(list(PQ), list(d)), sumsq_formula(list(d))), "t = (PQ·d)/‖d‖²",
                  (PQ.T * d)[0] / sum(c**2 for c in d), "Projection of PQ onto d gives the closest point.")
        F = B.add(point_formula(P, k, d), "Closest point F = P + t·d", V(P + k * d), f"t = {to_text(k)}.")
        QF = V(Q - F)
        answer = norm(B, QF, "distance ‖Q − F‖")
        label = "distance"
        facts.update(Q=Q, P=P, d=d, F=F)
    else:
        raise ProblemFormatError(f"unknown task {task!r}")
    return Solution(problem=p, steps=B.steps, answer=answer, answer_label=label, facts=facts, notes=notes)
