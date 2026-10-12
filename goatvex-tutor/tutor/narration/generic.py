"""Narration for any problem type, built from the verified steps.

Each step's label and reason were produced by the solver from verified
objects; they enter the narration only through placeholders ({op}, {why}).
``speak_text`` turns their Unicode math into words for the voice; the caption
shows the Unicode itself.
"""

from __future__ import annotations

import re

from tutor import registry
from tutor.narration.script import N, WORDS, Line, Spoken, V
from tutor.narration.spoken import int_words

SUPER = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))
SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉", "0123456789"))
SYMBOL_WORDS = [
    ("√", " the square root of "), ("∫", " the integral of "), ("→", " becomes "), ("↔", " swaps with "),
    ("≤", " is at most "), ("≥", " is at least "), ("≠", " is not equal to "), ("=", " equals "),
    ("·", " times "), ("×", " cross "), ("π", " pi "), ("θ", " theta "), ("λ", " lambda "), ("∞", " infinity "),
    ("′", " prime "), ("‖", " the length of "), ("|", " "), ("−", " minus "), ("+", " plus "), ("⁻¹", " inverse "),
    ("ᵀ", " transpose "), ("±", " plus or minus "),
]


def speak_text(text: str) -> str:
    """Best-effort spoken form of a Unicode math string (for TTS only; captions keep the original)."""
    t = text
    t = t.replace("⁻¹", "⁻¹ ")
    # superscript exponents: x² → x squared, x³ → x cubed, xⁿ → x to the n
    def sup(m):
        digits = "".join(SUPER.get(c, "") for c in m.group(0))
        if digits == "2":
            return " squared "
        if digits == "3":
            return " cubed "
        return f" to the power {digits} "
    t = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", sup, t)
    t = re.sub(r"[₀₁₂₃₄₅₆₇₈₉]+", lambda m: " " + "".join(SUB[c] for c in m.group(0)) + " ", t)
    t = re.sub(r"(?<=\w)/(?=\w|\()", " over ", t)
    t = re.sub(r"\^\(?", " to the power ", t).replace(")", " ").replace("(", " ")
    for sym, word in SYMBOL_WORDS:
        t = t.replace(sym, word)
    t = re.sub(r"(?<![\w])-(?=\d)", " negative ", t)
    t = re.sub(r"\bd/d(\w)", r" d by d \1 ", t)
    t = t.replace("ln", " natural log of ").replace("e^", " e to the ")
    return " ".join(t.split())


def S(text: str) -> Spoken:
    """Solver-produced text (built from verified objects) as a placeholder value."""
    return Spoken(speak_text(text), text)


def build(solution) -> dict:
    p = solution.problem
    pt = registry.get(p.type)
    script: dict = {
        "intro": Line("Let's work through this problem: {title}. First we'll see the idea, then every step, "
                      "each one checked by a computer.", {"title": S(pt.title.replace(" / ", " and "))}),
        "intuition": intuition_line(p.type),
    }
    steps = []
    for s in solution.steps:
        if s.kind == "setup" and s.id == "s0":
            continue
        why = s.justification if len(s.justification) < 260 else s.justification[:257] + "…"
        steps.append((s, Line("{op}. {why}", {"op": S(s.operation), "why": S(why)})))
    script["steps"] = steps
    from tutor.text.unicode_math import to_text

    ans = solution.answer
    shown = ", ".join(to_text(a) for a in ans) if isinstance(ans, list) else to_text(ans)
    script["result"] = Line("So the answer is {ans}.", {"ans": S(shown.replace("\n", " "))}) \
        if "\n" not in shown else Line("That's the answer, shown on screen.")
    script["check"] = Line("Every step you just saw was checked by a computer algebra system, and the final "
                           "answer was confirmed a second, independent way.")
    script["recap"] = recap_line(p.type)
    script["practice"] = Line("Now it's your turn. Pause the video and try this one. Your answer is checked in "
                              "the write-up.")
    return script


def _notation():
    import sympy as sp

    x, a, b, r = sp.symbols("x a b r", real=True)
    y = sp.Function("y")(x)
    return {
        "dydx": V(sp.Derivative(y, x)),
        "abi": V(a + b * sp.I),
        "ab": Spoken("a comma b", "(a, b)"),
        "r": V(r),
        "theta": Spoken("theta", "θ"),
        "isq": V(sp.Eq(sp.Pow(sp.I, 2, evaluate=False), -1, evaluate=False)),
        "y": Spoken("y", "y"),
    }


INTUITION = {
    "derivative": "The derivative is the slope of the tangent line at each point of the graph.",
    "tangent_line": "The tangent line touches the curve at the point and has the same slope there.",
    "implicit_derivative": "The curve may not be a single function, but near each point it is, and its slope is "
                           "{dydx}.",
    "log_differentiation": "Taking logarithms turns powers and products into sums, which are easy to differentiate.",
    "related_rates": "The quantities are tied together by an equation, so their rates of change are tied together "
                     "too.",
    "indefinite_integral": "An antiderivative undoes the derivative: differentiate the answer and you get back the "
                           "integrand.",
    "definite_integral": "The definite integral adds up signed area under the curve between the limits.",
    "ftc_derivative": "Differentiating an accumulated area gives back the height of the curve at the moving edge.",
    "riemann_sum": "Rectangles under the curve approximate the area; thinner rectangles do better.",
    "limit": "A limit asks what value the function approaches as the input gets close to the point, not its value "
             "there.",
    "determinant": "The determinant measures how the matrix scales area or volume, and its sign tells whether it "
                   "flips orientation.",
    "matrix_inverse": "The inverse matrix undoes what the original matrix does.",
    "cramers_rule": "Each unknown is a ratio of determinants.",
    "matrix_arithmetic": "Matrix products combine rows of the left matrix with columns of the right matrix.",
    "complex": "Complex numbers are points in the plane: {abi} sits at {ab}, at distance {r} from the origin and "
               "angle {theta}.",
    "geometry": "Vectors have length and direction; dot and cross products measure how a pair of vectors relate.",
    "rref": "Each equation is a line or a plane, and the solution is where they all meet.",
    "subspaces": "A span is everything you can reach with combinations of the vectors; a basis is a smallest set "
                 "that still reaches all of it.",
    "eigen": "Most vectors get turned by the matrix, but an eigenvector only gets stretched or flipped along its "
             "own direction.",
    "linear_transformation": "A linear transformation is decided by where it sends the standard basis vectors, "
                             "and those images are the columns of its matrix.",
    "orthogonality": "Projection drops a perpendicular onto the subspace; the closest point is the foot of that "
                     "perpendicular.",
    "optimization": "At a maximum or minimum inside the interval the graph is flat, so the tangent line is level; the "
                    "endpoints are candidates too.",
    "curve_sketching": "The first derivative tells where the graph rises and falls, and the second tells how it "
                       "bends.",
    "improper_integral": "An improper integral is a limit of ordinary integrals; it converges when the area "
                         "settles to a finite value.",
    "area_between_curves": "Slice the region into thin vertical strips; each strip reaches from the bottom curve up to the "
                           "top curve, and the integral adds them up.",
    "volume_of_revolution": "Spin the region around the axis; each thin slice becomes a disk, a washer, or a "
                            "shell, and the integral adds up their volumes.",
    "function_domain": "The domain is every input the formula can accept: no denominator that vanishes, no even root of "
                       "a value below the axis, no log of a value that is not positive.",
    "inverse_function": "The inverse undoes the function, so its graph is the mirror image across the diagonal "
                        "line through the origin.",
    "inverse_derivative": "Mirroring a graph across the diagonal flips each slope to its reciprocal.",
    "linearization": "Close to the point, the curve and its tangent line are almost the same, so the line gives a "
                     "good estimate.",
    "higher_derivative": "Each derivative measures how the previous derivative changes: slope, then bending, and so on.",
}

RECAPS = {
    "derivative": "Apply a single rule at a time: sums, constant multiples, powers, products, quotients, and the chain "
                  "rule from the outside in.",
    "tangent_line": "Find the point, find the slope from the derivative, then use point slope form.",
    "implicit_derivative": "Differentiate both sides, remember the chain rule on every {y}, then solve for {dydx}.",
    "log_differentiation": "Take the natural log of both sides, use log laws, differentiate, and multiply back.",
    "related_rates": "Write the relation, differentiate with respect to time, plug in the values at that moment, "
                     "and solve for the unknown rate.",
    "indefinite_integral": "Pick the right method, integrate piece by piece, substitute back, and add a "
                           "constant.",
    "definite_integral": "Find an antiderivative, evaluate it at the top limit, and subtract its value at the "
                         "bottom limit.",
    "ftc_derivative": "Put the upper limit into the integrand and multiply by its derivative.",
    "riemann_sum": "Find the width, list the sample points, evaluate the heights, add them up, and multiply by the "
                   "width.",
    "limit": "Try substitution first; if you get an indeterminate form, simplify, rationalize, or use "
             "L'Hôpital's rule.",
    "determinant": "Expand along the row or column with the most zeros, or row reduce while tracking swaps.",
    "matrix_inverse": "Row reduce the matrix beside the identity; when the left side becomes the identity, the "
                      "right side is the inverse.",
    "cramers_rule": "Find the determinant of the matrix, replace each column by the right side in turn, and divide.",
    "matrix_arithmetic": "Check the sizes first, then combine entries: rows with columns for products.",
    "complex": "Use {isq} to multiply, multiply by the conjugate to divide, and use polar form for powers and "
               "roots.",
    "geometry": "Turn the geometry into vectors, then use dot products for angles and cross products for normals.",
    "rref": "Get a leading one, clear the column below it, move on, then clear above from the right.",
    "subspaces": "Put the vectors in a matrix, row reduce, and read everything off the pivots.",
    "eigen": "Find the characteristic polynomial, its roots are the eigenvalues, and row reduce for each "
             "eigenspace.",
    "linear_transformation": "Check that the map respects sums and scalar multiples, then apply it to each "
                             "standard basis vector to build the matrix.",
    "orthogonality": "Subtract from each vector its projections onto the vectors already found, and keep what "
                     "is left.",
    "optimization": "Write the quantity as a function of a single variable, find the critical points, and compare "
                    "the candidates.",
    "curve_sketching": "Find the domain, intercepts and asymptotes, then the sign charts of the first and second "
                       "derivatives.",
    "improper_integral": "Replace the bad limit by a letter, integrate, and take the limit.",
    "area_between_curves": "Find where the curves meet, decide which curve is on top, and integrate the gap between "
                           "them.",
    "volume_of_revolution": "Choose disks, washers or shells, write the radius, and integrate.",
    "function_domain": "List every restriction, solve each one, and intersect the results.",
    "inverse_function": "Write the function, solve for the input, and swap the names.",
    "inverse_derivative": "Find the input that gives the point, differentiate there, and take the reciprocal.",
    "linearization": "Find the tangent line at a nearby easy point and use it as the estimate.",
    "higher_derivative": "Differentiate again and again, tidying up after each round.",
}


def intuition_line(ptype: str) -> Line:
    return Line(INTUITION.get(ptype, "Before computing, think about what the answer should look like."), _notation())


def recap_line(ptype: str) -> Line:
    return Line(RECAPS.get(ptype, "Break the problem into small steps, justify each one, and check the answer."),
                _notation())
